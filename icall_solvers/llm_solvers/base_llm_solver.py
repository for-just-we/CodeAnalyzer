import abc

from icall_solvers.base_solvers.base_matcher import BaseStaticMatcher
from llm_utils.base_analyzer import BaseLLMAnalyzer
from code_analyzer.definition_collector import BaseInfoCollector
from code_analyzer.schemas.ast_node import ASTNode

from typing import Dict, Set, DefaultDict
from collections import defaultdict

class BaseLLMSolver:
    def __init__(self, collector: BaseInfoCollector,
                 args,
                 base_analyzer: BaseStaticMatcher,
                 llm_analyzer: BaseLLMAnalyzer = None,
                 callsite_idxs: Dict[str, int] = None,
                 func_key_2_name: Dict[str, str] = None):
        self.collector: BaseInfoCollector = collector
        self.args = args
        # 保存类型匹配的callsite
        self.type_matched_callsites: Dict[str, Set[str]] = base_analyzer.callees.copy()
        additional_callsite_infos: DefaultDict[str, Set[str]] = defaultdict(set)
        if self.args.evaluate_uncertain:
            additional_callsite_infos = base_analyzer.uncertain_callees
        elif self.args.evaluate_soly_for_llm:
            additional_callsite_infos = base_analyzer.llm_declarator_analysis
        for key, values in additional_callsite_infos.items():
            self.type_matched_callsites[key] = self.type_matched_callsites.get(key, set()) | values

        # 保存语义匹配的callsite
        self.matched_callsites: DefaultDict[str, Set[str]] = defaultdict(set)
        self.macro_callsites: Set[str] = base_analyzer.macro_callsites

        self.llm_analyzer: BaseLLMAnalyzer = llm_analyzer
        self.callsite_idxs: Dict[str, int] = callsite_idxs
        self.func_key_2_name: Dict[str, str] = func_key_2_name

        self.icall_2_func: Dict[str, str] = base_analyzer.icall_2_func
        self.icall_nodes: Dict[str, ASTNode] = base_analyzer.icall_nodes

        self.expanded_macros: Dict[str, str] = base_analyzer.expanded_macros
        self.macro_call_exprs: Dict[str, str] = base_analyzer.macro_call_exprs

        if hasattr(base_analyzer, "kelp_cases"):
            self.kelp_cases = base_analyzer.kelp_cases
        if hasattr(base_analyzer, "mlta_cases"):
            self.mlta_cases = base_analyzer.mlta_cases

    @abc.abstractmethod
    def process_all(self):
        pass