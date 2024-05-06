import logging
import time
from typing import List, Tuple, Dict
from http import HTTPStatus
import dashscope
from dashscope.api_entities.dashscope_response import GenerationResponse

from llm_utils.base_analyzer import BaseLLMAnalyzer

class TongyiAnalyzer(BaseLLMAnalyzer):
    def __init__(self, model_type: str, api_key: str, temperature: float=0):
        super().__init__(model_type, temperature)
        self.api_key = api_key

    # 向通义千问发送一次请求，返回一个response，可能会触发异常
    def get_tongyi_response(self, dialog: List[Dict[str, str]], times: int) -> Tuple[str, bool, int]:
        """
        :param dialog: prompt sent to openai, its format is like:
                [{"role": "system", "content": "SYSTEM_PROMPT"},
                {"role": "user", "content": "USER_PROMPT"}]
        :return: first str is the response from openai or error message,
        second bool is whether the response is valid, True means valid, False means error occur
        third int is the times of retry
        error code refer to: https://help.aliyun.com/zh/dashscope/developer-reference/return-status-code-description
        temperature refer to: https://help.aliyun.com/zh/dashscope/developer-reference/api-details
        """
        try:
            response: GenerationResponse = dashscope.Generation.call(
                self.model_type,
                messages=dialog,
                api_key=self.api_key,
                result_format='message',  # set the result to be "message" format.
                temperature=self.temperature
            )
        except Exception as e:
            logging.getLogger("CodeAnalyzer").debug("encounter error: {}".format(e))
            return (str(e), False, times + 1)
        if response.status_code == HTTPStatus.OK:
            resp_text: str = response["output"]["choices"][0]["message"]["content"]
            input_token_num: int = response["usage"]["input_tokens"]
            output_token_num: int = response["usage"]["output_tokens"]
            self.input_token_num += input_token_num
            self.output_token_num += output_token_num

            self.max_input_token_num = max(self.max_input_token_num, input_token_num)
            self.max_output_token_num = max(self.max_output_token_num, output_token_num)
            self.max_total_token_num = max(self.max_total_token_num,
                                           input_token_num + output_token_num)
            if resp_text.strip() == "":
                resp = ("empty response", False, times)
            else:
                resp = (resp_text, True, times)
        # 403表示api key不能访问
        elif response.status_code in {401, 403}:
            logging.getLogger("CodeAnalyzer").info(response["message"])
            logging.getLogger("CodeAnalyzer").info("api key error")
            exit(-1)
        # rate limit
        elif response.status_code == 429:
            error_message = response["message"]
            if error_message == "Free allocated quota exceeded.":
                logging.getLogger("CodeAnalyzer").info("quota running out")
                exit(-1)
            logging.getLogger("CodeAnalyzer").debug("sleeping 60s due to rate limit")
            time.sleep(60)
            resp = (error_message, False, times)
        # 其它error
        else:
            error_message = response["message"]
            logging.getLogger("CodeAnalyzer").debug(error_message)
            resp = (error_message, False, times + 1)
        return resp

    def generate_response(self, diaglog: List[Dict[str, str]]) -> str:
        resp: Tuple[str, bool, int] = self.get_tongyi_response(diaglog, 0)
        # 没有成功解析出来，就最多重试3次
        while not resp[1]:
            if resp[2] >= 3:
                return "empty response"
            resp: Tuple[str, bool, int] = self.get_tongyi_response(diaglog, resp[2])
        content: str = resp[0]
        return content

    def get_response(self, contents: List[str], add_suffix: bool=False) -> str:
        dialog: List[Dict[str, str]] = self.generate_diaglog(contents)
        return self.generate_response(dialog)

    @property
    def model_name(self):
        return f"{self.model_type}-{self.temperature}"