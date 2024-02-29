import logging
import time
from typing import List, Tuple
import json
import requests
from icall_analyzer.llm.base_analyzer import BaseLLMAnalyzer
from icall_analyzer.llm.preprocess_prompt import preprocess_prompt

class HuggingFaceAnalyzer(BaseLLMAnalyzer):
    def __init__(self, model_type: str, address: str, temperature: float=0, max_new_tokens: int=20):
        super().__init__(model_type)
        self.address = "http://" + address + '/generate'
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens

    def get_hf_response(self, prompt: str, times: int) -> Tuple[str, bool, int]:
        """
        prompt: system_prompt + user_prompt
        """
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "inputs": prompt,
            "parameters": {"max_new_tokens": self.max_new_tokens,
                           "temperature": self.temperature}
        }
        response = requests.post(self.address, headers=headers, data=json.dumps(data))
        # 检查服务器的响应状态码
        if response.status_code == 200 and not response.text.startswith("Invalid:"):
            # 解析服务器的字符串响应
            response_data_json: dict = json.loads(response.text)
            resp_text: str = response_data_json['generated_text']
            return resp_text, True, times
        else:
            error_msg = "Error: Server returned a non-200 status code {} " \
                        "or return invalid response".format(response.status_code) \
                if response.status_code != 429 else "rate limit exceeded"
            logging.debug(error_msg)
            time.sleep(60)
            if response.status_code == 429:
                return error_msg, False, times
            return error_msg, False, times + 1

    def get_response(self, contents: List[str], add_suffix=False) -> str:
        assert len(contents) in {1, 2}
        prompt = preprocess_prompt(self.model_type, contents, add_suffix) #"\n\n".join(contents)
        resp: Tuple[str, bool, int] = self.get_hf_response(prompt, 0)
        # 没有成功解析出来，就最多重试3次
        while not resp[1]:
            if resp[2] >= 3:
                return ""
            resp: Tuple[str, bool, int] = self.get_hf_response(prompt, resp[2])
        content: str = resp[0]
        return content

    @property
    def model_name(self):
        return f"{self.model_type}-{self.temperature}"