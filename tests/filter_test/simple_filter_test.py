from llm_analyzer.simple_filter import SimpleFilter
from typing import Dict, Set, List
from llm_analyzer.llm_prompts import PREFIX, QUESTION_PROMPT, FORMAT_INSTRUCTIONS

def test_func(callsite_key: str, func_set: List[str], simple_filter: SimpleFilter):
    decl_contexts: List[str] = simple_filter.extract_decl_context(callsite_key)
    func_declarators: List[str] = [simple_filter.func_name_2_declarator.get(func, "")
                                   for func in func_set]

    print(PREFIX)
    print("====================")
    print(QUESTION_PROMPT.format(decl_contexts[-1], "\n".join(decl_contexts),
                                 "\n\n".join(func_declarators)))
    print("=========================")
    print(FORMAT_INSTRUCTIONS)