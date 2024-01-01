import logging
import time
from typing import List, Tuple
import tiktoken

import google.generativeai as genai
from google.generativeai import GenerativeModel
from google.generativeai.types.generation_types import GenerateContentResponse, GenerationConfig
from google.api_core.exceptions import ResourceExhausted, GoogleAPIError

from icall_analyzer.llm.base_analyzer import BaseLLMAnalyzer

ENCODING = "cl100k_base"

def num_tokens_from_string(string: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(ENCODING)
    num_tokens = len(encoding.encode(string))
    return num_tokens

class GeminiAnalyzer(BaseLLMAnalyzer):
    def __init__(self, model_type: str, api_key: str, temperature: float=0):
        super().__init__(model_type)
        genai.configure(api_key=api_key)
        self.temperature = temperature
        config = GenerationConfig(temperature=temperature)
        self.model: GenerativeModel = GenerativeModel(model_type, generation_config=config)

        # 只是用来记录输入和输出的token数
        self.input_token_num: int = 0
        self.output_token_num: int = 0

    # 向google发送一次请求，返回一个response，可能会触发异常
    def get_gemini_response(self, prompt: str, times: int) -> Tuple[str, bool, int]:
        """
        prompt: system_prompt + user_prompt
        """
        def handle_error(exception, sleep_time):
            error_message = f"{exception.__class__.__name__} in request, message is: {exception}"
            logging.debug(error_message)
            time.sleep(sleep_time)
            return str(exception), False, times

        try:
            self.input_token_num += num_tokens_from_string(prompt)
            response: GenerateContentResponse = self.model.generate_content(prompt)
            resp_text: str = response.text
            self.output_token_num += num_tokens_from_string(resp_text)
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
                return ""
            resp: Tuple[str, bool, int] = self.get_gemini_response(prompt, resp[2])
        content: str = resp[0]
        return content

    @property
    def model_name(self):
        return f"{self.model_type}-{self.temperature}"