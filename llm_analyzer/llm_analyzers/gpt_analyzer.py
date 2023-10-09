import logging

import openai
from llm_analyzer.llm_analyzers.base_analyzer import BaseLLMAnalyzer
from llm_analyzer.llm_prompts.llama_prompt import SystemPrompt1, UserPrompt1, \
    SystemPrompt2, UserPrompt2, SystemPrompt1_, UserPrompt1_
from llm_analyzer.parse_util import get_json_result
from typing import List, Dict

class GPTAnalyzer(BaseLLMAnalyzer):
    def __init__(self, api_key: str, model_type, num_per_batch=10):
        self.api_key = api_key
        self.num_per_batch = num_per_batch
        self.model_type = model_type

    def analyze_function_declarators(self, icall_context: List[str],
                                     func_name2declarator: Dict[str, str]) -> Dict[str, str]:
        remaining_func = set(func_name2declarator.keys())
        dialog1 = [{"role": "system",
                  "content": SystemPrompt1},
                 {"role": "user",
                  "content": UserPrompt1.format(icall_context[-1], "\n".join(icall_context),
                                                "\n\n".join(func_name2declarator.values()))}]
        openai.api_key = self.api_key
        response1 = openai.ChatCompletion.create(
            model=self.model_type,
            messages=dialog1
        )
        content1: str = response1.choices[0]["message"]["content"]
        logging.debug("raw content1: {}".format(content1))
        dialog2 = [{"role": "system", "content": SystemPrompt2},
                    {"role": "user", "content": UserPrompt2.format(content1)}]
        openai.api_key = self.api_key
        response2 = openai.ChatCompletion.create(
            model=self.model_type,
            messages=dialog2
        )
        content2: str = response2.choices[0]["message"]["content"]
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
        response1 = openai.ChatCompletion.create(
            model=self.model_type,
            messages=dialog1
        )
        content1: str = response1.choices[0]["message"]["content"]

        dialog2 = [{"role": "system",
                  "content": SystemPrompt2},
                {"role": "user",
                  "content": UserPrompt2.format(content1)}]
        response2 = openai.ChatCompletion.create(
            model=self.model_type,
            messages=dialog2
        )
        content2: str = response2.choices[0]["message"]["content"]

        json_items: Dict[str, str] = get_json_result(content2)
        json_result: Dict[str, str] = {key: value for key, value in json_items.items() if
                                       key in remaining_func}
        return json_result