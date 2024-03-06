import openai
from openai import OpenAI
import logging
import time
from typing import List, Dict, Tuple
from icall_analyzer.llm.base_analyzer import BaseLLMAnalyzer

openai_error_messages = {
    openai.APIError: "OpenAI API returned an API Error: {}",
    openai.APIConnectionError: "Failed to connect to OpenAI API: {}",
    openai.RateLimitError: "OpenAI TimeLimt: {}",
    openai.Timeout: "OpenAI API request timed out: {}",
    openai.BadRequestError: "Invalid request to OpenAI API: {}",
    openai.AuthenticationError: "Authentication error with OpenAI API: {}",
}

class OpenAIAnalyzer(BaseLLMAnalyzer):
    def __init__(self, model_type: str, api_key: str, address: str, temperature: float=0):
        super().__init__(model_type)
        # 必须有一个有效，如果访问远程openai服务器那么api-key不为空，如果访问本地模型那么base_url不为空
        assert not (api_key == "" and address == "")
        self.temperature = temperature

        # 只是用来记录输入和输出的token数
        self.input_token_num: int = 0
        self.output_token_num: int = 0

        # 远程访问openai模型
        if api_key != "":
            self.client = OpenAI(api_key=api_key)
            self.model_id = model_type
        # 本地vllm部署的模型
        else:
            url = "http://" + address + "/v1"
            self.client = OpenAI(api_key="EMPTY", base_url=url)
            model_type_2_id = {
                "qwen-1.5-14": "Qwen/Qwen1.5-14B-Chat",
                "qwen-1.5-72": "Qwen/Qwen1.5-72B-Chat"
            }
            self.model_id = model_type_2_id[model_type]

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
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=dialog,
                temperature=self.temperature
            )
            self.input_token_num += response.usage.prompt_tokens
            resp_text = response.choices[0]["message"]["content"]
            resp = (resp_text, True, times)
            self.output_token_num += response.usage.completion_tokens
            if resp_text.strip() == "":
                resp = ("empty response", False, times)

        except tuple(openai_error_messages.keys()) as e:
            error_type = type(e)
            error_message: str = openai_error_messages.get(error_type,
                                                      "An unknown error occurred: {}")
            # 如果达到了rate limit
            if error_type is not openai.RateLimitError:
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
                return "empty response"
            resp: Tuple[str, bool, int] = self.get_openai_response(diaglog, resp[2])
        content: str = resp[0]
        return content

    def get_response(self, contents: List[str], add_suffix: bool=False) -> str:
        dialog: List[Dict[str, str]] = self.generate_diaglog(contents)
        return self.generate_response(dialog)

    @property
    def model_name(self):
        return f"{self.model_type}-{self.temperature}"