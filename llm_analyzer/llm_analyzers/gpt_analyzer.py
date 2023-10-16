import logging
import openai
from llm_analyzer.llm_analyzers.base_analyzer import BaseLLMAnalyzer
from llm_analyzer.llm_prompts.llama_prompt import SystemPrompt1, UserPrompt1, \
    SystemPrompt2, UserPrompt2, SystemPrompt1_, UserPrompt1_
from llm_analyzer.parse_util import get_json_result
from typing import List, Dict

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
            openai.error.RateLimitError: "Failed to connect to OpenAI API: {}",
            openai.error.Timeout: "OpenAI API request timed out: {}",
            openai.error.InvalidRequestError: "Invalid request to OpenAI API: {}",
            openai.error.AuthenticationError: "Authentication error with OpenAI API: {}",
            openai.error.ServiceUnavailableError: "OpenAI API service unavailable: {}",
        }

        try:
            response = openai.ChatCompletion.create(
                model=self.model_type,
                messages=dialog
            )
        except tuple(error_messages.keys()) as e:
            error_type = type(e)
            error_message = error_messages.get(error_type, "An unknown error occurred: {}")
            logging.info(error_message.format(e))
            return ""
        return response.choices[0]["message"]["content"]

    def analyze_function_declarators(self, icall_context: List[str],
                                     func_name2declarator: Dict[str, str]) -> Dict[str, str]:
        remaining_func = set(func_name2declarator.keys())
        dialog1 = [{"role": "system",
                  "content": SystemPrompt1},
                 {"role": "user",
                  "content": UserPrompt1.format(icall_context[-1], "\n".join(icall_context),
                                                "\n\n".join(func_name2declarator.values()))}]
        content1: str = self.get_openai_response(dialog1)
        logging.debug("raw content1: {}".format(content1))
        dialog2 = [{"role": "system", "content": SystemPrompt2},
                    {"role": "user", "content": UserPrompt2.format(content1)}]
        content2: str = self.get_openai_response(dialog2)
        logging.debug("raw content2: {}".format(content2))
        logging.debug("=======================")
        json_items: Dict[str, str] = get_json_result(content2)
        json_result: Dict[str, str] = {key: value for key, value in json_items.items() if
                        key in remaining_func}
        return json_result

    def analyze_function_declarators_4_macro_call(self, icall_context: List[str],
                                     func_name2declarator: Dict[str, str],
                                     macro_content: str) -> Dict[str, str]:
        remaining_func = set(func_name2declarator.keys())
        dialog1 = [{"role": "system", "content": SystemPrompt1_},
                   {"role": "user", "content": UserPrompt1_.format(icall_context[-1], macro_content, "\n".join(icall_context)
                                                ,"\n\n".join(func_name2declarator.values()))}]
        content1: str = self.get_openai_response(dialog1)
        # 不浪费api key了
        if content1 == "":
            return {}
        dialog2 = [{"role": "system",
                  "content": SystemPrompt2},
                   {"role": "user",
                     "content": UserPrompt2.format(content1)}]
        content2: str = self.get_openai_response(dialog2)

        json_items: Dict[str, str] = get_json_result(content2)
        json_result: Dict[str, str] = {key: value for key, value in json_items.items() if
                                       key in remaining_func}
        return json_result