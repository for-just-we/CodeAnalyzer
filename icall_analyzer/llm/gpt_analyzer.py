import openai
import logging
import time
from typing import List, Dict, Tuple
from icall_analyzer.llm.base_analyzer import BaseLLMAnalyzer

openai_error_messages = {
    openai.error.APIError: "OpenAI API returned an API Error: {}",
    openai.error.APIConnectionError: "Failed to connect to OpenAI API: {}",
    openai.error.RateLimitError: "OpenAI TimeLimt: {}",
    openai.error.Timeout: "OpenAI API request timed out: {}",
    openai.error.InvalidRequestError: "Invalid request to OpenAI API: {}",
    openai.error.AuthenticationError: "Authentication error with OpenAI API: {}",
    openai.error.ServiceUnavailableError: "OpenAI API service unavailable: {}",
}

import tiktoken
ENCODING = "cl100k_base"


def num_tokens_from_string(string: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(ENCODING)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def get_num_tokens_for_dialog(dialog: List[Dict[str, str]]) -> int:
    num_tokens = 0
    for message in dialog:
        assert "content" in message.keys()
        num_tokens += num_tokens_from_string(message["content"])
    return num_tokens

class GPTAnalyzer(BaseLLMAnalyzer):
    def __init__(self, model_type: str, api_key: str, temperature: float=0):
        super().__init__(model_type)
        openai.api_key = api_key
        self.temperature = temperature

        # 只是用来记录输入和输出的token数
        self.input_token_num: int = 0
        self.output_token_num: int = 0

    # 向openai发送一次请求，返回一个response，可能会触发异常
    def get_openai_response(self, dialog: List[Dict[str, str]], times: int) -> Tuple[str, bool, int]:
        """
        :param dialog: prompt sent to openai, its format is like:
                [{"role": "system", "content": "SYSTEM_PROMPT"},
                {"role": "user", "content": "USER_PROMPT"}]
        :return: first str is the response from openai or error message,
        second bool is whether the response is valid, True means valid, False means error occur
        third int is the times of retry
        """
        try:
            response = openai.ChatCompletion.create(
                model=self.model_type,
                messages=dialog,
                temperature=self.temperature
            )
            self.input_token_num += get_num_tokens_for_dialog(dialog)
            resp = (response.choices[0]["message"]["content"], True, times)
            self.output_token_num += num_tokens_from_string(resp[0])
        except tuple(openai_error_messages.keys()) as e:
            error_type = type(e)
            error_message: str = openai_error_messages.get(error_type,
                                                      "An unknown error occurred: {}")
            # 如果达到了rate limit
            if error_type is not openai.error.RateLimitError:
                times += 1
                time.sleep(10)
                logging.debug("{}, sleeping 10s".format(error_message.format(e)))
            else:
                logging.debug("{}, sleeping 60s".format(error_message.format(e)))
                time.sleep(60)
            resp = (error_message.format(e), False, times)
        return resp

    def generate_response(self, diaglog: List[Dict[str, str]]) -> str:
        resp: Tuple[str, bool, int] = self.get_openai_response(diaglog, 0)
        # 没有成功解析出来，就最多重试3次
        while not resp[1]:
            if resp[2] >= 3:
                return ""
            resp: Tuple[str, bool, int] = self.get_openai_response(diaglog, resp[2])
        content: str = resp[0]
        return content

    def get_response(self, contents: List[str], add_suffix: bool=False) -> str:
        dialog: List[Dict[str, str]] = self.generate_diaglog(contents)
        return self.generate_response(dialog)

    @property
    def model_name(self):
        return f"{self.model_type}-{self.temperature}"