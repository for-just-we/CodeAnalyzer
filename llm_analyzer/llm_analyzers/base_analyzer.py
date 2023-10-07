from typing import List, Dict

class BaseLLMAnalyzer:
    def analyze(self):
        pass

    def analyze_function_declarators(self, icall_context: List[str],
                                     func_name2declarator: Dict[str, str]) -> Dict[str, str]:
        return {}

    def analyze_function_declarators_4_macro_call(self, icall_context: List[str],
                                     func_name2declarator: Dict[str, str],
                                     macro_content: str) -> Dict[str, str]:
        return {}