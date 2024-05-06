import logging
import time
from typing import List, Dict, Tuple
from llm_utils.base_analyzer import BaseLLMAnalyzer
from zhipuai import ZhipuAI, APIReachLimitError, APIStatusError
from zhipuai.api_resource.chat.completions import Completion

class ZhipuAnalyzer(BaseLLMAnalyzer):
    def __init__(self, model_type: str, api_key: str, address: str, temperature: float=0):
        super().__init__(model_type, temperature)
        if api_key != "":
            self.client = ZhipuAI(api_key=api_key)
        else:
            base_url = "http://" + address + "/v1/"
            self.client = ZhipuAI(api_key="EMP.TY", base_url=base_url)

    # 向zhipu发送一次请求，返回一个response，可能会触发异常
    def get_glm_response(self, dialog: List[Dict[str, str]], times: int) -> Tuple[str, bool, int]:
        """
        :param dialog: prompt sent to openai, its format is like:
                [{"role": "system", "content": "SYSTEM_PROMPT"},
                {"role": "user", "content": "USER_PROMPT"}]
        :return: first str is the response from openai or error message,
        second bool is whether the response is valid, True means valid, False means error occur
        third int is the times of retry
        """
        try:
            response: Completion = self.client.chat.completions.create(
                model=self.model_type,
                messages=dialog,
                temperature=self.temperature
            )
            resp_text: str = response.choices[0].message.content
            if resp_text.strip() != "":
                resp = (resp_text, True, times)
            else:
                resp = ("empty response", False, times)
            self.input_token_num += response.usage.prompt_tokens
            self.output_token_num += response.usage.completion_tokens

            self.max_input_token_num = max(self.max_input_token_num,
                                           response.usage.prompt_tokens)
            self.max_output_token_num = max(self.max_output_token_num,
                                            response.usage.completion_tokens)

            self.max_total_token_num = max(self.max_total_token_num,
                                           response.usage.prompt_tokens + response.usage.completion_tokens)


        except APIReachLimitError as e:
            # 如果达到了rate limit
            time.sleep(60)
            logging.getLogger("CodeAnalyzer").debug("{}, sleeping 60s".format(e))
            resp = (str(e), False, times)
        except APIStatusError as e:
            # 如果达到了rate limit
            time.sleep(10)
            times += 1
            logging.getLogger("CodeAnalyzer").debug("{}, sleeping 10s".format(e))
            resp = (str(e), False, times)
        except Exception as e:
            time.sleep(20)
            times += 1
            logging.getLogger("CodeAnalyzer").debug("{}, sleeping 20s".format(e))
            resp = (str(e), False, times)

        return resp


    def generate_response(self, diaglog: List[Dict[str, str]]) -> str:
        resp: Tuple[str, bool, int] = self.get_glm_response(diaglog, 0)
        # 没有成功解析出来，就最多重试3次
        while not resp[1]:
            if resp[2] >= 3:
                return "empty response"
            resp: Tuple[str, bool, int] = self.get_glm_response(diaglog, resp[2])
        content: str = resp[0]
        return content


    def get_response(self, contents: List[str], add_suffix: bool=False) -> str:
        dialog: List[Dict[str, str]] = self.generate_diaglog(contents)
        return self.generate_response(dialog)


    @property
    def model_name(self):
        return f"{self.model_type}-{self.temperature}"