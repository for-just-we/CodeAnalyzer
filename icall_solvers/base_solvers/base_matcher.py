import abc
from tqdm import tqdm
from typing import Dict, DefaultDict, Set, List, Tuple
from collections import defaultdict

from code_analyzer.visitors.util_visitor import get_top_level_expr, get_local_top_level_expr
from code_analyzer.schemas.ast_node import ASTNode
from code_analyzer.definition_collector import BaseInfoCollector

class BaseStaticMatcher:
    def __init__(self):
        # 分析过的callsite
        self.analyzed_callsites: Set[str] = set()
        # 在function内没有被成功分析的case
        self.local_failed_callsites: Set[str] = set()

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


class BaseInfoAnalyzer:
    def __init__(self, collector: BaseInfoCollector,
                 raw_global_addr_sites: Dict[str, List[ASTNode]],
                 raw_local_addr_sites: Dict[str, Dict[str, List[ASTNode]]]):
        self.collector: BaseInfoCollector = collector

        # global scope的address-taken site只需要考虑init_declarator
        self.global_addr_sites: Dict[str, List[Tuple[ASTNode, int, ASTNode]]] = dict()
        # local scope的address-taken site考虑init_declarator, assignment_expression, argument_list,
        # conditional_expression
        self.local_declarators: DefaultDict[str, DefaultDict[str, List[Tuple[ASTNode, int, ASTNode]]]] = defaultdict(
            lambda: defaultdict(list))
        self.local_assignment_exprs: DefaultDict[
            str, DefaultDict[str, List[Tuple[ASTNode, int, ASTNode]]]] = defaultdict(
            lambda: defaultdict(list))
        self.local_call_expr: DefaultDict[str, List[Tuple[ASTNode, int]]] = defaultdict(list)
        self.call_expr_arg_idx: DefaultDict[str, List[Tuple[str, int]]] = defaultdict(list)

        self.pre_analyze(raw_global_addr_sites, raw_local_addr_sites)


    def pre_analyze(self, raw_global_addr_sites: Dict[str, List[ASTNode]],
                    raw_local_addr_sites: Dict[str, Dict[str, List[ASTNode]]]):
        # 全局declarator分析
        for func_name, nodes in tqdm(raw_global_addr_sites.items(), desc="collecting raw declarators"):
            decl_nodes: List[Tuple[ASTNode, int, ASTNode]] = list()
            for node in nodes:
                top_level_node, initializer_level = get_top_level_expr(node)
                if top_level_node is None:
                    continue
                if top_level_node.node_type == "init_declarator":
                    decl_nodes.append((top_level_node, initializer_level, node))

            decl_nodes: List[Tuple[ASTNode, int, ASTNode]] = \
                list(map(lambda x: (x[0], x[1], x[2]), decl_nodes))

            if len(decl_nodes) > 0:
                self.global_addr_sites[func_name] = decl_nodes

        # local declarator分析
        for func_name, node_in_func in tqdm(raw_local_addr_sites.items(), desc="collecting local declarators"):
            for func_key, nodes in node_in_func.items():
                for node in nodes:
                    top_level_node, initializer_level = get_local_top_level_expr(node)
                    if top_level_node is None:
                        continue
                    if top_level_node.node_type == "init_declarator":
                        self.local_declarators[func_name][func_key].append((top_level_node,
                                                                            initializer_level, node))

                    elif top_level_node.node_type == "assignment_expression" or \
                        (top_level_node.node_type == "conditional_expression"
                         and hasattr(top_level_node, "assignment_expression")):
                        self.local_assignment_exprs[func_name][func_key].append((top_level_node,
                                                                                 initializer_level, node))


                    elif top_level_node.node_type == "call_expression":
                        self.local_call_expr[func_name].append((top_level_node, initializer_level))


    @abc.abstractmethod
    def analyze(self):
        pass