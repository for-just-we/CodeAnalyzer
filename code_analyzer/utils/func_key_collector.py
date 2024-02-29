from typing import Dict, DefaultDict, Set

def get_all_func_keys(callees: Dict[str, Set[str]],
                      llm_declarator_analysis: DefaultDict[str, Set[str]]) -> Set[str]:
    total_func_keys: Set[str] = set()
    total_func_keys |= set.union(*callees.values())
    total_func_keys |= set.union(*llm_declarator_analysis.values())
    return total_func_keys