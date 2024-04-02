from code_analyzer.utils.addr_taken_sites_util import get_init_node
from code_analyzer.definition_collector import BaseInfoCollector
from code_analyzer.schemas.function_info import FuncInfo
from code_analyzer.schemas.ast_node import ASTNode
from code_analyzer.visitors.util_visitor import ConfinedFuncPointerCollector, arg_num_match, \
    IdentifierExtractor, get_local_top_level_expr, ExprAnalyzer
from code_analyzer.visit_utils.type_util import parsing_type, get_original_type
from icall_solvers.base_solvers.base_matcher import BaseInfoAnalyzer
from icall_solvers.base_solvers.mlta.type_confine_analyzer import get_init_idx_list
from code_analyzer.visitors.base_func_visitor import LocalGlobalRefVisitor
from code_analyzer.utils.addr_taken_sites_util import extract_addr_site

from typing import DefaultDict, Set, Dict, List, Union, Tuple
from collections import defaultdict
from tqdm import tqdm


# 1.通过call expression的参数传值。
# 2.通过全局变量直接调用，全局变量不应被reassign。
# 3.通过局部变量直接调用。
# 不考虑数组，结构体
class ConfineFuncAnalyzer(BaseInfoAnalyzer):
    def __init__(self, collector: BaseInfoCollector,
                 raw_global_addr_sites: Dict[str, List[ASTNode]],
                 raw_local_addr_sites: Dict[str, Dict[str, List[ASTNode]]]):
        super().__init__(collector, raw_global_addr_sites, raw_local_addr_sites)
        # 保留被赋值给指定icall的func name
        self.func_name2icall_key: DefaultDict[str, Set[str]] = defaultdict(set)
        self.func_name2global_vars: DefaultDict[str, Set[str]] = defaultdict(set)

        self.global_var_field2func: DefaultDict[tuple, Set[str]] = defaultdict(set)
        self.global_var2func: DefaultDict[str, Set[str]] = defaultdict(set)
        self.global_var2affected_callsites: DefaultDict[str, Set[str]] = defaultdict(set)
        # func key -> local var -> func names
        self.simple_local_var2func: DefaultDict[str, DefaultDict[str, Set[str]]]\
            = defaultdict(lambda :defaultdict(set))

        self.simple_df_globals: Set[str] = set()
        self.complex_df_globals: Set[str] = set()

        self.simple_df_locals: DefaultDict[str, Set[str]] = defaultdict(set)
        self.complex_df_locals: DefaultDict[str, Set[str]] = defaultdict(set)
        self.complex_df_func_locals: Set[str] = set()

    # 先只关注通过call expression传递的function，
    # 同时被call expression传递的icall通通标记为simple function pointer
    def analyze(self):
        # 处理call语句
        # 首先分析每个address-taken function的参数索引
        for func_name, call_nodes in tqdm(self.local_call_expr.items(), desc="grouping call expressions for kelp"):
            for call_node, arg_idx in call_nodes:
                callee_func_name = call_node.children[0].node_text
                arg_num = call_node.argument_list.child_count
                target_funcs: List[str] = list(
                    filter(lambda func_key: self.collector.func_info_dict[func_key].func_name == callee_func_name
                                            and arg_num_match(arg_num, self.collector.func_info_dict[func_key]),
                           self.collector.func_info_dict.keys()))
                if len(target_funcs) <= 0:
                    # 如果是宏函数
                    continue
                else:
                    for target_func_key in target_funcs:
                        self.call_expr_arg_idx[func_name].append((target_func_key, arg_idx))

        # 首先分析每个address-taken function的参数索引
        for func_name, call_expr_arg_idxs in tqdm(self.call_expr_arg_idx.items(),
                                          desc="analyzing call expr for kelp"):
            # 确保只通过call expression进行了传值
            if func_name in self.local_declarators.keys(): # | self.local_assignment_exprs.keys():
                continue

            for func_key, arg_idx in call_expr_arg_idxs:
                traversed_func_names = set()
                flag = self.traverse_call(func_name, func_key, arg_idx, traversed_func_names)
                # 不是confined function
                if not flag:
                    if func_name in self.func_name2icall_key.keys():
                        self.func_name2icall_key.pop(func_name)
                    break

        # 分析全局变量
        for func_name, declarator_infos in tqdm(self.global_addr_sites.items(), desc="analyzing global declarators for kelp"):
            for addr_taken_site_top, init_level, addr_taken_site in declarator_infos:
                self.retrive_info_from_global_declarator(addr_taken_site_top,
                                                         addr_taken_site, init_level,
                                                         addr_taken_site.node_text)


        # 分析局部变量，当addr-taken function被赋值给函数指针后，函数指针不能接着赋值给别的变量或者作为参数传递给其它调用，
        # 必须在当前函数内
        for func_name, assignment_infos in tqdm(self.local_assignment_exprs.items(),
                                                desc="analyzing assignment expressions for kelp"):
            for func_key, assignment_info in assignment_infos.items():
                for addr_taken_site_top, init_level, addr_taken_site in assignment_info:
                    self.retrive_info_from_assignment(addr_taken_site_top, func_key, addr_taken_site.node_text)



    def traverse_call(self, func_name: str, func_key: str, idx: int, traversed_func_names: Set[str]) -> bool:
        func_info: FuncInfo = self.collector.func_info_dict[func_key]
        if len(func_info.parameter_types) <= idx:
            return True
        # 防止递归
        if func_info.func_name in traversed_func_names:
            return True
        traversed_func_names.add(func_info.func_name)

        param_name = func_info.parameter_types[idx][1]
        func_pointer_collector = ConfinedFuncPointerCollector(param_name)
        func_pointer_collector.traverse_node(func_info.func_body)

        # 处理assignment语句，如果有assignment，直接认为是complex data flow
        if len(func_pointer_collector.assignment_node_infos) > 0:
            return False

        for call_node in func_pointer_collector.callsites:
            callsite_key: str = f"{func_info.file}:" \
                                f"{call_node.start_point[0] + 1}:" \
                                f"{call_node.start_point[1] + 1}"
            self.func_name2icall_key[func_name].add(callsite_key)

        # 递归遍历call
        for call_node, arg_idx in func_pointer_collector.call_nodes:
            caller_func_name = call_node.children[0].node_text
            # 需要检查是否存在宏调用
            target_func_keys: List[str] = list(
                filter(lambda func_key: self.collector.func_info_dict[func_key].func_name == caller_func_name,
                        self.collector.func_info_dict.keys()))
            for target_func_key in target_func_keys:
                flag = self.traverse_call(func_name, target_func_key, arg_idx, traversed_func_names)
                # 如果func_name被赋值给了别的变量
                if not flag:
                    return False

        return True


    def retrive_info_from_global_declarator(self, node: ASTNode, func_node: ASTNode, initializer_level: int,
                                            func_name: str):
        assert node.node_type == "init_declarator"
        # 默认取整个initializer
        init_level_in_need = initializer_level
        var_node = node.children[0]
        identifier_extractor = IdentifierExtractor()
        identifier_extractor.traverse_node(var_node)

        if identifier_extractor.is_function:
            return ("", "", node.parent.node_text)

        var_name = identifier_extractor.var_name

        if var_name not in self.collector.global_var_info.keys():
            return ("", "", node.parent.node_text)

        # 判断var_name是不是simple data flow
        self.func_name2global_vars[func_name].add(var_name)
        is_simple_flag = self.is_global_simple_data_flow(var_name)
        if not is_simple_flag:
            return

        var_type = self.collector.global_var_info[var_name]
        var_type, pointer_level = parsing_type((var_type, 0))
        ori_var_type, pointer_level = get_original_type((var_type, pointer_level),
                                                        self.collector.type_alias_infos)
        # 结构体initializer
        if ori_var_type in self.collector.struct_name2declarator.keys():
            # 如果是结构体数组类型
            if pointer_level > 0:
                return
            init_level_in_need -= pointer_level
            if init_level_in_need <= 0:
                init_level_in_need = 1
            init_node = get_init_node(func_node, init_level_in_need)

            if init_node is None:
                return

            idx_list: List[Union[int, str]] = get_init_idx_list(func_node, init_node)
            fields: List[str] = self.get_struct_field(var_name, ori_var_type, idx_list)
            # 成功解析结构体类型全局变量
            if len(fields) > 0:
                self.global_var_field2func[tuple(fields)].add(func_name)

        # 如果是其它类型
        else:
            self.global_var2func[var_name].add(func_name)


    def get_struct_field(self, var_name: str, base_struct_name: str, idx_list: List[int]) -> List[str]:
        fields: List[str] = [var_name]
        cur_struct = base_struct_name
        for i, idx in enumerate(idx_list):
            if isinstance(idx, str):
                field_name = idx
            else:
                if cur_struct not in self.collector.struct_field_list.keys():
                    return []
                if len(self.collector.struct_field_list[cur_struct]) <= idx:
                    return []
                field_name = self.collector.struct_field_list[cur_struct][idx]
            fields.append(field_name)

            if i == len(idx_list) - 1:
                return fields
            field_type = self.collector.struct_infos[cur_struct].get(field_name, "")
            if field_type == "":
                return []
            field_type, pointer_level = parsing_type((field_type, 0))
            ori_var_type, pointer_level = get_original_type((field_type, pointer_level),
                                                            self.collector.type_alias_infos)
            cur_struct = ori_var_type

        return []


    # 判断全局变量是不是simple data flow，也就是全局变量是否会赋值给其它变量或者被重新写入
    def is_global_simple_data_flow(self, var_name: str) -> bool:
        if var_name in self.simple_df_globals:
            return True
        elif var_name in self.complex_df_globals:
            return False

        local_refer_sites_per_func_key: DefaultDict[str, DefaultDict[str, List[ASTNode]]] = \
            defaultdict(lambda: defaultdict(list))
        # 收集在其它函数中的使用情况，不能在assignment expression和declarator中出现
        for func_key, func_info in self.collector.func_info_dict.items():
            arg_names: Set[str] = set([param[1] for param in func_info.parameter_types])
            local_global_var_visitor = LocalGlobalRefVisitor(self.collector.func_names,
                                                             set(func_info.local_var.keys()),
                                                             arg_names, var_name,
                                                             self.collector.macro_defs)
            local_global_var_visitor.traverse_node(func_info.func_body)
            assert len(local_global_var_visitor.local_refer_sites.keys()) <= 1
            for var_name, refer_sites in local_global_var_visitor.local_refer_sites.items():
                local_refer_sites_per_func_key[var_name][func_key].extend(refer_sites)

        raw_local_addr_sites: Dict[str, Dict[str, List[ASTNode]]] = dict()
        for var_name, local_refer_sites in local_refer_sites_per_func_key.items():
            raw_local_addr_sites[var_name] = extract_addr_site(local_refer_sites)

        local_call_expr: DefaultDict[str, List[Tuple[ASTNode, int]]] = defaultdict(list)

        # local declarator分析
        for var_name, node_in_func in raw_local_addr_sites.items():
            for func_key, nodes in node_in_func.items():
                for node in nodes:
                    top_level_node, initializer_level = get_local_top_level_expr(node)
                    if top_level_node is None:
                        continue
                    if top_level_node.node_type == "init_declarator":
                        self.complex_df_globals.add(var_name)
                        return False

                    elif top_level_node.node_type == "assignment_expression" or \
                            (top_level_node.node_type == "conditional_expression"
                                and hasattr(top_level_node, "assignment_expression")):
                         self.complex_df_globals.add(var_name)
                         return False


                    elif top_level_node.node_type == "call_expression":
                        local_call_expr[var_name].append((top_level_node, initializer_level))

        # call group
        call_expr_arg_idx: DefaultDict[str, List[Tuple[str, int]]] = defaultdict(list)
        for var_name, call_nodes in local_call_expr.items():
            for call_node, arg_idx in call_nodes:
                callee_func_name = call_node.children[0].node_text
                arg_num = call_node.argument_list.child_count
                target_funcs: List[str] = list(
                    filter(lambda func_key: self.collector.func_info_dict[func_key].func_name == callee_func_name
                                            and arg_num_match(arg_num, self.collector.func_info_dict[func_key]),
                           self.collector.func_info_dict.keys()))
                if len(target_funcs) <= 0:
                    # 如果是宏函数
                    continue
                else:
                    for target_func_key in target_funcs:
                        call_expr_arg_idx[var_name].append((target_func_key, arg_idx))

        # traversing call
        for var_name, call_expr_arg_idxs in call_expr_arg_idx.items():
            for func_key, arg_idx in call_expr_arg_idxs:
                traversed_func_names = set()
                flag = self.traverse_call_for_global(var_name, func_key, arg_idx, traversed_func_names)
                # 不是simple global var
                if not flag:
                    self.complex_df_globals.add(var_name)
                    return False

        self.simple_df_globals.add(var_name)
        return True


    def traverse_call_for_global(self, var_name: str,  func_key: str, idx: int,
                                   traversed_func_names: Set[str]) -> bool:
        func_info: FuncInfo = self.collector.func_info_dict[func_key]
        if len(func_info.parameter_types) <= idx:
            return True
        # 防止递归
        if func_info.func_name in traversed_func_names:
            return True
        traversed_func_names.add(func_info.func_name)

        param_name = func_info.parameter_types[idx][1]
        func_pointer_collector = ConfinedFuncPointerCollector(param_name)
        func_pointer_collector.traverse_node(func_info.func_body)

        # 处理assignment语句，如果有assignment，直接认为是complex data flow
        if len(func_pointer_collector.assignment_node_infos) > 0 or len(func_pointer_collector.init_node_infos) > 0:
            return False

        # 处理所有调用点包括该identifier的语句
        for call_node in func_pointer_collector.callsites:
            callsite_key = f"{func_info.file}:{call_node.start_point[0] + 1}" \
                           f":{call_node.start_point[1] + 1}"
            self.global_var2affected_callsites[var_name].add(callsite_key)


        # 递归遍历call
        for call_node, arg_idx in func_pointer_collector.call_nodes:
            caller_func_name = call_node.children[0].node_text
            # 需要检查是否存在宏调用
            target_func_keys: List[str] = list(
                filter(lambda func_key: self.collector.func_info_dict[func_key].func_name == caller_func_name,
                       self.collector.func_info_dict.keys()))
            for target_func_key in target_func_keys:
                flag = self.traverse_call_for_global(var_name, target_func_key, arg_idx, traversed_func_names)
                # 如果func_name被赋值给了别的变量
                if not flag:
                    return False

        return True


    def retrive_info_from_assignment(self, node: ASTNode, func_key: str,
                                     func_name: str):
        # c++语法可能导致错误
        if not (node.node_type == "assignment_expression" and node.child_count == 3):
            return
        var_node = node.children[0]
        # 如果被赋值的不是简单变量，是结构体访问等复杂变量，跳过
        expr_analyzer = ExprAnalyzer()
        expr_analyzer.traverse_node(var_node)

        # 传值给了complex variable
        if len(expr_analyzer.identifiers) != 1:
            self.complex_df_func_locals.add(func_name)
            return
        # 被赋值的局部变量名
        var_name = expr_analyzer.identifiers[0]
        # 判断局部变量的data flow是不是complex data flow
        is_simple_flag = self.is_simple_local_df(var_name, func_key)
        # 如果该赋值语句将函数赋值给complex data flow
        if not is_simple_flag:
            self.complex_df_func_locals.add(func_name)
            return

        self.simple_local_var2func[func_key][var_name].add(func_name)



    def is_simple_local_df(self, var_name: str, func_key: str) -> bool:
        if var_name in self.simple_df_locals[func_key]:
            return True
        elif var_name in self.complex_df_locals[func_key]:
            return True
        # 局部变量表
        func_info = self.collector.func_info_dict[func_key]
        # 确保被赋值的局部变量没有complex data flow
        # - 没有赋值给别的变量，没有被传值给函数参数
        arg_names: Set[str] = set([param[1] for param in func_info.parameter_types])
        local_var_visitor = LocalGlobalRefVisitor(self.collector.func_names,
                                                  set(func_info.local_var.keys()),
                                                  arg_names, var_name,
                                                  self.collector.macro_defs)
        local_var_visitor.traverse_node(func_info.func_body)
        assert len(local_var_visitor.local_refer_sites.keys()) <= 1

        for var_name, refer_sites in local_var_visitor.local_refer_sites.items():
            # 局部变量为complex data flow
            new_refered_sites: List[ASTNode] = list()
            for refer_site in refer_sites:
                top_level_node, initializer_level = get_local_top_level_expr(refer_site)
                if top_level_node is None:
                    continue
                if top_level_node.node_type == "init_declarator":
                    new_refered_sites.append(refer_site)

                elif top_level_node.node_type == "assignment_expression" or \
                        (top_level_node.node_type == "conditional_expression"
                            and hasattr(top_level_node, "assignment_expression")):
                    new_refered_sites.append(refer_site)

                elif top_level_node.node_type == "call_expression":
                    if initializer_level != -1:
                        new_refered_sites.append(refer_site)

            if len(new_refered_sites) > 0:
                self.complex_df_locals[func_key].add(var_name)
                return False

        self.simple_df_locals[func_key].add(var_name)
        return True