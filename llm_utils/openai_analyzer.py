from openai import OpenAI
from openai import APIError, APIConnectionError, RateLimitError, Timeout, BadRequestError, AuthenticationError, OpenAIError
import logging
import time
from typing import List, Dict, Tuple
from llm_utils.base_analyzer import BaseLLMAnalyzer

openai_error_messages = {
    APIError: "OpenAI API returned an API Error: {}",
    APIConnectionError: "Failed to connect to OpenAI API: {}",
    RateLimitError: "OpenAI TimeLimt: {}",
    Timeout: "OpenAI API request timed out: {}",
    BadRequestError: "Invalid request to OpenAI API: {}",
    AuthenticationError: "Authentication error with OpenAI API: {}",
}

model_name_map: Dict[str, Dict[str, str]] = {
    "swift": {
        "Qwen1.5-72B-Chat": "qwen1half-72b-chat",
        "Qwen1.5-32B-Chat": "qwen1half-32b-chat",
        "Qwen1.5-14B-Chat": "qwen1half-14b-chat",

        "llama-3-70b-instruct": "llama3-70b-instruct",
        "llama-3-8b-instruct": "llama3-8b-instruct"
    }
}

class OpenAIAnalyzer(BaseLLMAnalyzer):
    def __init__(self, model_type: str, api_key: str, address: str, temperature: float = 0,
                 max_tokens: int = 0, server_type = "other", add_llama3_stop: bool = False,
                 disable_system_prompt: bool = False):
        super().__init__(model_type, temperature)
        # 必须有一个有效，如果访问远程openai服务器那么api-key不为空，如果访问本地模型那么base_url不为空
        assert not (api_key == "" and address == "")
        self.max_tokens = max_tokens
        self.add_llama3_stop = add_llama3_stop

        self.request_model_name = model_name_map.get(server_type,
                                                     dict()).get(model_type, model_type)
        self.disable_system_prompt = disable_system_prompt

        # 远程访问openai模型
        if api_key != "":
            self.client = OpenAI(api_key=api_key)
        # 本地vllm部署的模型
        else:
            url = "http://" + address + "/v1"
            self.client = OpenAI(api_key="EMPTY", base_url=url)

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
            params = {
                "model": self.request_model_name,
                "messages": dialog,
                "temperature": self.temperature
            }
            # 如果max_tokens不为零，添加到参数中
            if self.max_tokens != 0:
                params["max_tokens"] = self.max_tokens
            if self.add_llama3_stop:
                params["stop"] = ["<|start_header_id|>", "<|end_header_id|>", "<|eot_id|>", "<|reserved_special_token"]
            # 调用completions.create()方法
            response = self.client.chat.completions.create(**params)
            self.input_token_num += response.usage.prompt_tokens
            self.max_input_token_num = max(self.max_input_token_num, response.usage.prompt_tokens)

            resp_text = response.choices[0].message.content
            resp = (resp_text, True, times)

            self.output_token_num += response.usage.completion_tokens
            self.max_output_token_num = max(self.max_output_token_num,
                                            response.usage.completion_tokens)

            self.max_total_token_num = max(self.max_total_token_num,
                        response.usage.prompt_tokens + response.usage.completion_tokens)
            if resp_text.strip() == "":
                resp = ("empty response", False, times)

        except OpenAIError as e:
            error_type = type(e)
            error_message: str = openai_error_messages.get(error_type,
                                                      "An unknown error occurred: {}")
            # 如果达到了rate limit
            if error_type is not RateLimitError:
                times += 1
                time.sleep(10)
                logging.getLogger("CodeAnalyzer").debug("{}, sleeping 10s".format(error_message.format(e)))
            else:
                logging.getLogger("CodeAnalyzer").debug("{}, sleeping 60s".format(error_message.format(e)))
                time.sleep(60)
            resp = (error_message.format(e), False, times)

        except Exception as e:
            times += 1
            time.sleep(10)
            logging.getLogger("CodeAnalyzer").debug("{}, sleeping 10s".format("An unknown error occurred: {}".format(e)))
            resp = ("An unknown error occurred: {}".format(e), False, times)

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
        if len(contents) == 2 and self.disable_system_prompt:
            contents = ["\n\n".join(contents)]
        dialog: List[Dict[str, str]] = self.generate_diaglog(contents)
        return self.generate_response(dialog)

    @property
    def model_name(self):
        return f"{self.model_type}-{self.temperature}"