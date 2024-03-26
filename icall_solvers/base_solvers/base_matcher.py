import abc
from typing import Dict, DefaultDict, Set
from collections import defaultdict
from code_analyzer.schemas.ast_node import ASTNode

class BaseStaticMatcher:
    def __init__(self):
        # 保存匹配上的函数名
        self.callees: DefaultDict[str, Set[str]] = defaultdict(set)
        # 如果uncertain
        self.uncertain_callees: DefaultDict[str, Set[str]] = defaultdict(set)
        self.uncertain_idxs: DefaultDict[str, Dict[str, Set[int]]] = defaultdict(dict)
        self.llm_declarator_analysis: DefaultDict[str, Set[str]] = defaultdict(set)
        # 通过cast分析后得到的matching result
        self.cast_callees: DefaultDict[str, Set[str]] = defaultdict(set)

        self.expanded_macros: Dict[str, str] = dict()
        self.macro_call_exprs: Dict[str, str] = dict()

        self.icall_2_decl_text: Dict[str, str] = dict()
        self.icall_2_decl_type_text: Dict[str, str] = dict()
        self.icall_2_struct_name: Dict[str, str] = dict()

        self.macro_callsites: Set[str] = set()
        # 保存每个indirect-callsite所在的function
        self.icall_2_func: Dict[str, str] = dict()
        # 保存每个indirect-callsite的ASTNode
        self.icall_nodes: Dict[str, ASTNode] = dict()

    @abc.abstractmethod
    def process_all(self):
        pass