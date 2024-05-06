import logging
import time
from typing import List, Tuple
import tiktoken

import google.generativeai as genai
from google.generativeai import GenerativeModel
from google.generativeai.types.generation_types import GenerateContentResponse, GenerationConfig
from google.generativeai.text import Completion
from google.generativeai.discuss import ChatResponse
from google.api_core.exceptions import ResourceExhausted, GoogleAPIError

from llm_utils.base_analyzer import BaseLLMAnalyzer

ENCODING = "cl100k_base"

def num_tokens_from_string(string: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(ENCODING)
    num_tokens = len(encoding.encode(string))
    return num_tokens

class GoogleAnalyzer(BaseLLMAnalyzer):
    def __init__(self, model_type: str, api_key: str, temperature: float=0):
        super().__init__(model_type, temperature)
        genai.configure(api_key=api_key)
        config = GenerationConfig(temperature=temperature)
        if model_type == "gemini-pro":
            self.model: GenerativeModel = GenerativeModel(model_type, generation_config=config)

    def send_text_to_llm(self, prompt: str) -> str:
        if self.model_type == "gemini-pro":
            response: GenerateContentResponse = self.model.generate_content(prompt)
            resp_text: str = response.text
        elif self.model_type == "text-bison-001":
            response: Completion = genai.generate_text(
                model='models/text-bison-001', prompt=prompt,
                temperature=self.temperature, max_output_tokens=1024)
            resp_text: str = response.result
        elif self.model_type == "chat-bison-001":
            chat: ChatResponse = genai.chat(model="models/chat-bison-001",
                                            messages=[prompt], temperature=0.8)
            resp_text: str = chat.last
        else:
            msg = "unsupported model type {}".format(self.model_type)
            raise RuntimeError(msg)
        return resp_text

    # 向google发送一次请求，返回一个response，可能会触发异常
    def get_gemini_response(self, prompt: str, times: int) -> Tuple[str, bool, int]:
        """
        prompt: system_prompt + user_prompt
        """
        def handle_error(exception, sleep_time):
            error_message = f"{exception.__class__.__name__} in request, message is: {exception}"
            logging.getLogger("CodeAnalyzer").debug(error_message)
            time.sleep(sleep_time)
            return str(exception), False, times

        try:
            input_num = num_tokens_from_string(prompt)
            self.input_token_num += input_num
            self.max_input_token_num = max(self.max_input_token_num, input_num)
            resp_text: str = self.send_text_to_llm(prompt)
            if resp_text is None or resp_text == "":
                return "empty response", False, times + 1
            output_num = num_tokens_from_string(resp_text)
            self.output_token_num += output_num
            self.max_output_token_num = max(self.max_output_token_num, output_num)

            self.max_total_token_num = max(self.max_total_token_num, input_num + output_num)
            return resp_text, True, times
        # 达到rate limit
        except ResourceExhausted as e:
            return handle_error(e, 60)
        # 其他GoogleAPIError或者没有返回text
        except (GoogleAPIError, ValueError, IndexError) as e:
            times += 1
            return handle_error(e, 30)

    def get_response(self, contents: List[str], add_suffix: bool=False) -> str:
        assert len(contents) in {1, 2}
        prompt = "\n\n".join(contents)
        resp: Tuple[str, bool, int] = self.get_gemini_response(prompt, 0)
        # 没有成功解析出来，就最多重试3次
        while not resp[1]:
            if resp[2] >= 3:
                return "empty response"
            resp: Tuple[str, bool, int] = self.get_gemini_response(prompt, resp[2])
        content: str = resp[0]
        return content

    @property
    def model_name(self):
        return f"{self.model_type}-{self.temperature}"