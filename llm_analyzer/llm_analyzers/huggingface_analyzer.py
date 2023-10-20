from llm_analyzer.parse_util import get_json_result
from llm_analyzer.llm_analyzers.base_analyzer import BaseLLMAnalyzer
from llm_analyzer.llm_prompts.gpt_prompt import SystemPrompt1, SystemPrompt1_, \
    UserPrompt1, UserPrompt1_, UserPrompt2
from typing import List, Dict
from llm_analyzer.parse_util import batch_dict
import logging

# ToDo
class HuggingFaceAnalyzer(BaseLLMAnalyzer):
    def __init__(self, service_url, max_new_token=1024, max_tried_per_times=5):
        self.service_url = f"{service_url}/generate"

    # def generate(self, dialogs: List[Dialog]) -> List[str]:
    #     results: List[ChatPrediction] = self.model.chat_completion(
    #         dialogs,  # type: ignore
    #     )
    #     contents: List[str] = [output['generation']['content'] for output in results]
    #     return contents

    # def analyze_function_declarator(self, icall_context: List[str],
    #                                 func_name2declarator: Dict[str, str]) -> Dict[str, str]:
    #     # count = 0
    #     final_result = {}
    #     remaining_func = set(func_name2declarator.keys())
    #     # while len(remaining_func) > 0 and count < self.max_tried_per_times:
    #     batch_func_name2declarator: List[Dict[str, str]] = batch_dict(func_name2declarator, self.num_per_batch)
    #     # declarators: List[str] = [func_name2declarator[func_name] for func_name in remaining_func]
    #     dialogs1: List[Dialog] = [
    #             [{"role": "system",
    #               "content": SystemPrompt1},
    #              {"role": "user",
    #               "content": UserPrompt1.format(icall_context[-1], "\n".join(icall_context),
    #                                             "\n\n".join(func_name_declarators.values()))}]
    #             for func_name_declarators in batch_func_name2declarator
    #         ]
    #     contents1: List[str] = self.generate(dialogs1)
    #     dialogs2: List[Dialog] = [
    #             [
    #              {"role": "user",
    #                 "content": UserPrompt2.format(content1)}
    #              ]
    #                 for content1 in contents1
    #         ]
    #     contents2: List[str] = self.generate(dialogs2)
    #     json_result: Dict[str, str] = dict()
    #     for content2 in contents2:
    #         json_result.update({key: value for key, value in get_json_result(content2).items() if
    #                                        key in remaining_func})
    #     final_result.update(json_result)
    #     return final_result
    #
    #
    # def analyze_function_declarators_4_macro_call(self, icall_context: List[str],
    #                                  func_name2declarator: Dict[str, str],
    #                                  macro_content: str) -> Dict[str, str]:
    #     final_result = {}
    #     remaining_func = set(func_name2declarator.keys())
    #     batch_func_name2declarator: List[Dict[str, str]] = batch_dict(func_name2declarator, self.num_per_batch)
    #     # while len(remaining_func) > 0 and count < self.max_tried_per_times:
    #     # declarators: List[str] = [func_name2declarator[func_name] for func_name in remaining_func]
    #     dialogs1: List[Dialog] = [
    #             [{"role": "system",
    #               "content": SystemPrompt1_},
    #              {"role": "user",
    #               "content": UserPrompt1_.format(icall_context[-1], macro_content, "\n".join(icall_context)
    #                                             ,"\n\n".join(func_name_declarators.values()))}]
    #             for func_name_declarators in batch_func_name2declarator
    #     ]
    #     contents1: List[str] = self.generate(dialogs1)
    #     dialogs2: List[Dialog] = [
    #         [{"role": "system",
    #               "content": SystemPrompt2},
    #             {"role": "user",
    #               "content": UserPrompt2.format(content1)}]
    #         for content1 in contents1
    #     ]
    #     contents2: List[str] = self.generate(dialogs2)
    #     json_result: Dict[str, str] = dict()
    #     for content2 in contents2:
    #         json_result.update({key: value for key, value in get_json_result(content2).items() if
    #                                        key in remaining_func})
    #         final_result.update(json_result)
    #     return final_result