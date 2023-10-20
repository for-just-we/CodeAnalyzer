from typing import List, Dict

class BaseLLMAnalyzer:
    def analyze(self):
        pass

    def analyze_function_declarator(self, icall_context: List[str],
                                    func_name: str, func_declarator: str) -> bool:
        return True

    def analyze_function_declarators_4_macro_call(self, icall_context: List[str],
                                    func_name: str, func_declarator: str,
                                     macro_content: str) -> bool:
        return True