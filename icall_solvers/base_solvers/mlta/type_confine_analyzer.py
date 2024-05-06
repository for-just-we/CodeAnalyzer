from code_analyzer.utils.addr_taken_sites_util import get_init_node
from code_analyzer.definition_collector import BaseInfoCollector
from code_analyzer.schemas.function_info import FuncInfo
from typing import DefaultDict, Set, Dict, List, Union
from collections import defaultdict
from code_analyzer.visit_utils.type_util import parsing_type, get_original_type
from code_analyzer.visitors.util_visitor import VarAnalyzer, IdentifierExtractor, arg_num_match

from icall_solvers.base_solvers.base_matcher import BaseInfoAnalyzer
from code_analyzer.schemas.ast_node import ASTNode
from code_analyzer.visitors.util_visitor import FuncPointerCollector
from tqdm import tqdm


class TypeConfineAnalyzer(BaseInfoAnalyzer):
    def __init__(self, collector: BaseInfoCollector,
                 raw_global_addr_sites: Dict[str, List[ASTNode]],
                 raw_local_addr_sites: Dict[str, Dict[str, List[ASTNode]]]):
        super().__init__(collector, raw_global_addr_sites, raw_local_addr_sites)
        self.struct_name_2_field_4_type: DefaultDict[str, DefaultDict[str,
                       Set[str]]] = defaultdict(lambda: defaultdict(set))
        self.var_analyzer: VarAnalyzer = VarAnalyzer(collector)


    def analyze(self):
        # global init declarator
        for func_name, declarator_infos in tqdm(self.global_addr_sites.items(), desc="analyzing global declarators", ncols=200):
            for addr_taken_site_top, init_level, addr_taken_site in declarator_infos:
                self.retrive_info_from_declarator(addr_taken_site_top,
                                                  addr_taken_site, init_level,
                                                  self.collector.global_var_info,
                                                  addr_taken_site.node_text)

        # local init declarator
        for func_name, local_declarator_infos in tqdm(self.local_declarators.items(), desc="analyzing local declarators", ncols=200):
            for func_key, declarator_infos in local_declarator_infos.items():
                for addr_taken_site_top, init_level, addr_taken_site in declarator_infos:
                    self.retrive_info_from_declarator(addr_taken_site_top,
                                             addr_taken_site, init_level,
                                             self.collector.func_info_dict[func_key].local_var,
                                             addr_taken_site.node_text)

        # 处理assignment语句
        for func_name, assignment_infos in tqdm(self.local_assignment_exprs.items(), desc="analyzing assignment expressions", ncols=200):
            for func_key, assignment_info in assignment_infos.items():
                for addr_taken_site_top, init_level, addr_taken_site in assignment_info:
                    self.retrive_info_from_assignment(addr_taken_site_top, func_key, addr_taken_site, addr_taken_site.node_text)

        # 处理call语句
        # 首先分析每个address-taken function的参数索引
        for func_name, call_nodes in tqdm(self.local_call_expr.items(), desc="grouping call expressions for mlta", ncols=200):
            for call_node, arg_idx in call_nodes:
                callee_func_name = call_node.children[0].node_text
                arg_num = call_node.argument_list.child_count
                target_funcs: List[str] = list(filter(lambda func_key: self.collector.func_info_dict[func_key].func_name == callee_func_name
                                                      and arg_num_match(arg_num, self.collector.func_info_dict[func_key]),
                       self.collector.func_info_dict.keys()))
                if len(target_funcs) <= 0:
                    # 如果是宏函数
                    continue
                else:
                    for target_func_key in target_funcs:
                        self.call_expr_arg_idx[func_name].append((target_func_key, arg_idx))

        # 然后递归进入call-chain进行type confine分析
        for func_name, call_expr_arg_idxs in \
            tqdm(self.call_expr_arg_idx.items(), desc="type confine for call expr in mlta", ncols=200):
            for func_key, arg_idx in call_expr_arg_idxs:
                traversed_func_names = set()
                self.traverse_call(func_name, func_key, arg_idx, traversed_func_names)


    def retrive_info_from_declarator(self, node: ASTNode, func_node: ASTNode, initializer_level: int,
                                     var_info: Dict[str, str], func_name: str):
        assert node.node_type == "init_declarator"
        # 默认取整个initializer
        init_level_in_need = initializer_level
        var_node = node.children[0]
        identifier_extractor = IdentifierExtractor()
        identifier_extractor.traverse_node(var_node)

        if identifier_extractor.is_function_type \
            or identifier_extractor.is_function:
            return ("", "", node.parent.node_text)

        var_name = identifier_extractor.var_name

        if var_name not in var_info.keys():
            return ("", "", node.parent.node_text)

        var_type = var_info[var_name]
        var_type, pointer_level = parsing_type((var_type, 0))
        ori_var_type, pointer_level = get_original_type((var_type, pointer_level),
                                                        self.collector.type_alias_infos)
        # 结构体initializer
        if ori_var_type in self.collector.struct_name2declarator.keys():
            init_level_in_need -= pointer_level
            if init_level_in_need <= 0:
                init_level_in_need = 1
            init_node = get_init_node(func_node, init_level_in_need)

            if init_node is None:
                return

            idx_list: List[Union[int, str]] = get_init_idx_list(func_node, init_node)
            base_struct, field_name = self.get_struct_field(ori_var_type, idx_list)
            if base_struct != "" and field_name != "":
                self.struct_name_2_field_4_type[base_struct][field_name].add(func_name)


    def retrive_info_from_assignment(self, node: ASTNode, func_key: str, addr_taken_site: ASTNode,
                                     func_name: str):
        # c++语法可能导致错误
        cur_node = node
        if cur_node.node_type == "conditional_expression" and hasattr(cur_node, "assignment_expression"):
            cur_node = cur_node.assignment_expression
        if not (cur_node.node_type == "assignment_expression" and cur_node.child_count == 3):
            return ("", "", "", cur_node.children[0].node_text, cur_node.node_text)
        assert cur_node.node_type == "assignment_expression" and cur_node.child_count == 3
        declarator, refered_struct_name, base_type, field_name = \
            self.var_analyzer.analyze_var(cur_node.children[0], func_key)

        # 如果是struct的赋值，直接给struct用initializer_list赋初值
        if base_type in self.collector.struct_infos.keys() and \
            cur_node.children[2].node_type == "initializer_list":
            idx_list: List[Union[int, str]] = get_init_idx_list(addr_taken_site, cur_node.children[2])
            base_struct, field__name = self.get_struct_field(refered_struct_name, idx_list)
            if base_struct != "" and field_name != "":
                refered_struct_name = base_struct
                field_name = field__name

        if refered_struct_name != "" and field_name != "":
            self.struct_name_2_field_4_type[refered_struct_name][field_name].add(func_name)



    def get_struct_field(self, base_struct_name: str, idx_list: List[int]):
        cur_struct = base_struct_name
        for i, idx in enumerate(idx_list):
            if isinstance(idx, str):
                field_name = idx
            else:
                if cur_struct not in self.collector.struct_field_list.keys():
                    return ("", "")
                if len(self.collector.struct_field_list[cur_struct]) <= idx:
                    return ("", "")
                field_name = self.collector.struct_field_list[cur_struct][idx]

            if i == len(idx_list) - 1:
                return (cur_struct, field_name)
            field_type = self.collector.struct_infos[cur_struct].get(field_name, "")
            if field_type == "":
                return ("", "")
            field_type, pointer_level = parsing_type((field_type, 0))
            ori_var_type, pointer_level = get_original_type((field_type, pointer_level),
                                                            self.collector.type_alias_infos)
            cur_struct = ori_var_type

        return ("", "")


    def traverse_call(self, func_name: str, func_key: str, idx: int, traversed_func_names: Set[str]):
        func_info: FuncInfo = self.collector.func_info_dict[func_key]
        if len(func_info.parameter_types) <= idx:
            return
        # 防止递归
        if func_info.func_name in traversed_func_names:
            return
        traversed_func_names.add(func_info.func_name)
        # 获取对应参数
        param_name = func_info.parameter_types[idx][1]
        func_pointer_collector = FuncPointerCollector(param_name)
        func_pointer_collector.traverse_node(func_info.func_body)

        # 遍历assignment
        for addr_taken_node, initializer_level, top_level_node in func_pointer_collector.assignment_node_infos:
            # var_node为被赋值的变量，top_level_node为赋值语句
            self.retrive_info_from_assignment(top_level_node, func_key, addr_taken_node, func_name)

        # 遍历init_declarator
        for addr_taken_node, initializer_level, top_level_node in func_pointer_collector.init_node_infos:
            self.retrive_info_from_declarator(top_level_node, addr_taken_node,
                                              initializer_level, func_info.local_var,
                                              func_name)

        # 递归遍历call
        for call_node, arg_idx in func_pointer_collector.call_nodes:
            caller_func_name = call_node.children[0].node_text
            # 需要检查是否存在宏调用
            target_func_keys: List[str] = list(filter(lambda func_key: self.collector.func_info_dict[func_key].func_name == caller_func_name,
                                                       self.collector.func_info_dict.keys()))
            for target_func_key in target_func_keys:
                self.traverse_call(func_name, target_func_key, arg_idx, traversed_func_names)


def get_init_idx_list(func_node: ASTNode, top_level_node: ASTNode):
    idx_list: List[Union[int, str]] = list()
    cur_node = func_node
    while cur_node != top_level_node:
        if cur_node.parent.node_type == "initializer_list":
            if cur_node.node_type == "initializer_pair":
                field_designator = cur_node.field_designator
                if isinstance(field_designator, ASTNode):
                    idx_list.append(field_designator.node_text[1:])
                elif isinstance(field_designator, list):
                    for designator in list(reversed(field_designator)):
                        idx_list.append(designator.node_text[1:])
            else:
                idx_list.append(cur_node.parent.children.index(cur_node))
        cur_node = cur_node.parent
    return list(reversed(idx_list))