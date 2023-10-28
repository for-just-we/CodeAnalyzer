import logging
import time

import openai
from llm_analyzer.llm_analyzers.base_analyzer import BaseLLMAnalyzer
from llm_analyzer.llm_prompts.gpt_prompt import SystemPrompt1, UserPrompt1, \
    UserPrompt2, SystemPrompt1_, UserPrompt1_
from llm_analyzer.parse_util import get_final_answer, Answer
from typing import List, Dict

log_tmp = """User:{}
================================================
GPT1:{}
================================================
User2:{}
================================================
GPT2:{}
================================================
Answer:{}
"""

class GPTAnalyzer(BaseLLMAnalyzer):
    def __init__(self, api_key: str, model_type, num_per_batch=10):
        openai.api_key = api_key
        self.num_per_batch = num_per_batch
        self.model_type = model_type

    def get_openai_response(self, dialog: List[Dict[str, str]]) -> str:
        # 错误处理参考：https://medium.com/codingthesmartway-com-blog/mastering-openai-error-handling-your-comprehensive-guide-to-smooth-api-interactions-72b202c670c6
        error_messages = {
            openai.error.APIError: "OpenAI API returned an API Error: {}",
            openai.error.APIConnectionError: "Failed to connect to OpenAI API: {}",
            openai.error.RateLimitError: "OpenAI TimeLimt: {}",
            openai.error.Timeout: "OpenAI API request timed out: {}",
            openai.error.InvalidRequestError: "Invalid request to OpenAI API: {}",
            openai.error.AuthenticationError: "Authentication error with OpenAI API: {}",
            openai.error.ServiceUnavailableError: "OpenAI API service unavailable: {}",
        }
        times = 0
        while True:
            if times == 3:
                return ""
            try:
                response = openai.ChatCompletion.create(
                    model=self.model_type,
                    messages=dialog
                )
                break
            except tuple(error_messages.keys()) as e:
                error_type = type(e)
                error_message = error_messages.get(error_type, "An unknown error occurred: {}")
                logging.info(error_message.format(e))
                # 如果达到了rate limit
                if error_type is not openai.error.RateLimitError:
                    times += 1
                    time.sleep(10)
                else:
                    time.sleep(60)
                continue
        return response.choices[0]["message"]["content"]

    # 一个个处理
    def analyze_function_declarator(self, icall_context: List[str],
                                    func_name: str, func_declarator: str,
                                    log_file: str = None) -> bool:
        user_input = UserPrompt1.format(icall_context[-1], "\n".join(icall_context),
                                                func_declarator)
        dialog1 = [{"role": "system",
                  "content": SystemPrompt1},
                 {"role": "user",
                  "content": user_input}]
        content1: str = self.get_openai_response(dialog1)
        if content1 == "":
            return True
        content1 = self.get_openai_response(dialog1)
        logging.debug("raw content1: {}".format(content1))
        dialog2 = [{"role": "user", "content": UserPrompt2.format(content1)}]
        content2: str = self.get_openai_response(dialog2)
        logging.debug("raw content2: {}".format(content2))
        logging.debug("=======================")
        answer: Answer = get_final_answer(content2)

        if log_file is not None:
            file_content: str = log_tmp.format(SystemPrompt1 + "\n" + user_input,
                                               content1, UserPrompt2.format(content1),
                                               content2, str(answer != Answer.no))
            open(log_file, 'w', encoding='utf-8').write(file_content)
        # yes/uncertain返回1，no返回0
        return answer != Answer.no

    def analyze_function_declarators_4_macro_call(self, icall_context: List[str],
                                                  func_name: str, func_declarator: str,
                                     macro_content: str, log_file: str = None) -> bool:
        user_input = UserPrompt1_.format(icall_context[-1], macro_content, "\n".join(icall_context)
                                                ,func_declarator)
        dialog1 = [{"role": "system", "content": SystemPrompt1_},
                   {"role": "user", "content": user_input}]
        content1: str = self.get_openai_response(dialog1)
        # 不浪费api key了，这个answer不确定
        # 如果连续3次访问错误，跳过这个函数的查询
        count = 0
        while content1 == "":
            if count == 3:
                return True
            content1 = self.get_openai_response(dialog1)
            count += 1
        dialog2 = [{"role": "user",
                     "content": UserPrompt2.format(content1)}]
        content2: str = self.get_openai_response(dialog2)

        answer: Answer = get_final_answer(content2)

        if log_file is not None:
            file_content: str = log_tmp.format(SystemPrompt1 + "\n" + user_input,
                                               content1, UserPrompt2.format(content1),
                                               content2, str(answer != Answer.no))
            open(log_file, 'w', encoding='utf-8').write(file_content)

        return answer != Answer.no