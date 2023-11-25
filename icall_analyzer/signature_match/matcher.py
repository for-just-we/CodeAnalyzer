from code_analyzer.definition_collector import BaseInfoCollector
from code_analyzer.visit_utils.base_util import loc_inside
from code_analyzer.visit_utils.type_util import parsing_type, get_original_type
from code_analyzer.schemas.function_info import FuncInfo
from code_analyzer.visitors.func_visitor import FunctionBodyVisitor
from scope_strategy.base_strategy import BaseStrategy
from tree_sitter import Node

from tqdm import tqdm
from typing import Dict, List, Tuple, Set
import logging

class TypeAnalyzer:
    def __init__(self, collector: BaseInfoCollector,
                 scope_strategy: BaseStrategy = None):
        self.collector: BaseInfoCollector = collector
        # 保存每个indirect-callsite的代码文本
        self.icall_nodes: Dict[str, Node] = dict()
        # 保存每个indirect-callsite所在的function
        self.icall_2_func: Dict[str, str] = dict()
        # scope策略
        self.scope_strategy: BaseStrategy = scope_strategy

        # 保存匹配上的函数名
        self.callees: Dict[str, Set[str]] = dict()
        # 将宏函数间接调用点映射为宏名称
        self.macro_icall2_callexpr: Dict[str, str] = dict()
        # 保存每个indirect-callsite的代码文本
        self.icall_nodes: Dict[str, Node] = dict()
        # 保存每个indirect-callsite所在的function
        self.icall_2_func: Dict[str, str] = dict()

    def process_all(self):
        # 遍历每个函数
        for func_key, func_info in tqdm(self.collector.func_info_dict.items(), desc="processing functions"):
            icall_locs: List[Tuple[int, int]] = self.collector.icall_dict.get(
                func_info.file, list())
            start_point: Tuple[int, int] = func_info.func_body.start_point
            end_point: Tuple[int, int] = func_info.func_body.end_point
            icall_locs_in_cur_func: List[Tuple[int, int]] = list(filter(
                lambda icall_loc: loc_inside(icall_loc, start_point, end_point),
                icall_locs
            ))

            # 当前函数中存在indirect-callsite
            if len(icall_locs_in_cur_func) > 0:
                self.process_function(func_key, func_info, icall_locs_in_cur_func)

    # 处理一个函数中的indirect-call
    def process_function(self, func_key: str, func_info: FuncInfo, icall_locs: List[Tuple[int, int]]):
        arg_info: Dict[str, str] = {parameter_type[1]: parameter_type[0]
                                       for parameter_type in func_info.parameter_types}
        func_body_visitor: FunctionBodyVisitor = FunctionBodyVisitor(
            icall_locs, arg_info, func_info.local_var, self.collector)
        # 设置局部变量和形参涉及到函数指针的信息
        if hasattr(func_info, "func_var2param_types"):
            func_body_visitor.set_func_var2param_types(func_info.func_var2param_types)
        if hasattr(func_info, "func_param2param_types"):
            func_body_visitor.set_func_param2param_types(func_info.func_param2param_types)
        func_body_visitor.traverse_node(func_info.func_body)
        if hasattr(func_info, "var_arg_func_param"):
            func_body_visitor.set_var_arg_func_param(func_info.var_arg_func_param)
        if hasattr(func_info, "var_arg_func_var"):
            func_body_visitor.set_var_arg_func_var(func_info.var_arg_func_var)

        # 遍历当前function中的每一个indirect-call
        for icall_loc in icall_locs:
            callsite_key: str = f"{func_info.file}:{icall_loc[0] + 1}:{icall_loc[1] + 1}"
            # 如果该indirect-call对应的call expression没有被正确解析，跳过。
            if icall_loc not in func_body_visitor.icall_nodes.keys():
                self.callees[callsite_key] = set()
                continue
            self.icall_nodes[callsite_key] = func_body_visitor.icall_nodes[icall_loc]
            self.icall_2_func[callsite_key] = func_key
            self.process_indirect_call(callsite_key, icall_loc, func_body_visitor)

    # 处理一个indirect-call
    def process_indirect_call(self, callsite_key: str, icall_loc: Tuple[int, int],
                              func_body_visitor: FunctionBodyVisitor):
        # 如果不是宏函数
        if icall_loc not in func_body_visitor.current_macro_funcs.keys():
            # 根据参数的类型进行间接调用匹配
            arg_type: List[Tuple[str, int]] = \
                func_body_visitor.arg_info_4_callsite.get(icall_loc)
            if arg_type is not None:
                self.match_with_types(arg_type, callsite_key)
            else:
                logging.debug("error parsing arguments for indirect-callsite: {}".
                              format(callsite_key))

            # 根据函数指针声明的形参类型进行匹配
            func_pointer_arg_type: List[str] = func_body_visitor.icall_2_decl_param_types.\
                get(icall_loc, None)
            if func_pointer_arg_type is not None:
                func_pointer_arg_types: List[Tuple[str, int]] = [
                    (t, 0) for t in func_pointer_arg_type
                ]
                var_arg: bool = (icall_loc in func_body_visitor.var_arg_icalls)
                self.match_with_types(func_pointer_arg_types, callsite_key, var_arg)
            else:
                logging.debug("fail to find function pointer declaration for indirect-callsite: {}".
                              format(callsite_key))


    # 根据形参签名匹配indirect-call对应的潜在callee
    def match_with_types(self, arg_type: List[Tuple[str, int]], callsite_key: str,
                         var_arg: bool = False):
        if callsite_key not in self.callees.keys():
            self.callees[callsite_key] = set()
        # 参数数量
        arg_num: int = len(arg_type)
        fixed_arg_type: List[Tuple[str, int]] = list()
        for arg_t in arg_type:
            src_type, pointer_level = parsing_type(arg_t)
            fixed_arg_type.append(get_original_type((src_type, pointer_level),
                                                    self.collector.type_alias_infos))
        func_set: Set[str] = set()

        def process_func_set(func_keys: Set[str],
                             cur_fixed_arg_type: List[Tuple[str, int]]):
            new_func_keys = func_keys.copy()
            if self.scope_strategy is not None:
                new_func_keys = set(filter(lambda func_key:
                                           self.scope_strategy.analyze_key(callsite_key, func_key)
                                           and func_key not in self.callees[callsite_key],
                                           new_func_keys))
            for func_key in new_func_keys:
                # 基于callsite的形参和call target实参进行类型匹配
                param_types: List[Tuple[str, int]] = self.collector.param_types.get(func_key)
                flag = self.match_types_callsite_target(cur_fixed_arg_type,
                                                        param_types[:len(cur_fixed_arg_type)])
                # 如果匹配成功
                if flag:
                    func_set.add(func_key)

        # 遍历固定参数数量的函数列表
        fixed_num_func_keys: Set[str] = self.collector.param_nums_2_func_keys.get(arg_num, {})
        process_func_set(fixed_num_func_keys, fixed_arg_type)

        # 遍历可变参数函数列表
        for param_num, func_keys in self.collector.var_arg_param_nums_2_func_keys.items():
            # 可能被调用
            if param_num <= arg_num:
                process_func_set(func_keys, fixed_arg_type[: param_num])
            # 如果indirect-callsite和call target都支持可变参数，并且target参数多于callsite
            elif var_arg and param_num > arg_num:
                process_func_set(func_keys, fixed_arg_type)

        # 如果arg_types支持可变参数
        if var_arg:
            # 遍历固定参数函数列表中形参数量大于arg_num的函数
            for param_num, func_keys in self.collector.param_nums_2_func_keys.items():
                # 可能被调用
                if param_num > arg_num:
                    process_func_set(func_keys, fixed_arg_type)

        self.callees[callsite_key].update(func_set)

    # 根据参数类型进行匹配
    def match_types_callsite_target(self, arg_types: List[Tuple[str, int]],
                                    param_types: List[Tuple[str, int]]) -> bool:
        assert len(arg_types) == len(param_types)
        flag = True
        # 逐个参数匹配
        for i in range(len(arg_types)):
            arg_type: Tuple[str, int] = arg_types[i]
            param_type: Tuple[str, int] = param_types[i]
            flag &= self.match_type(arg_type, param_type)
        return flag

    def match_type(self, arg_type: Tuple[str, int], param_type: Tuple[str, int]) -> bool:
        # 如果严格类型匹配成功
        if arg_type[0] == param_type[0] and arg_type[1] == param_type[1]:
            return True
        # 考虑结构体、联合体之间的的指针类型转换关系
        # 如果都不是指针类型，不予考虑
        if arg_type[1] == 0 and param_type[1] == 0:
            return False
        if self.is_type_contain(arg_type, param_type):
            return True
        elif self.is_type_contain(param_type, arg_type):
            return True
        return False

    # 确认类型1是否可能包含类型2
    def is_type_contain(self, type1: Tuple[str, int], type2: Tuple[str, int]) -> bool:
        # 如果type1不是结构体类型，不予考虑
        if type1[0] not in self.collector.struct_infos.keys():
            return False
        first_field_of_type1 = self.collector.struct_first_field_types.get(type1[0],
                                                                           None)
        # 查不到第一个field的类型
        if first_field_of_type1 is None:
            return False
        src_type_name, pointer_level = parsing_type((first_field_of_type1, 0))
        src_type: Tuple[str, int] = get_original_type((src_type_name, pointer_level),
                                                      self.collector.type_alias_infos)
        # 如果第一个field的类型和type2相同
        if src_type[0] == type2[0] and src_type[1] + type1[1] == type2[1]:
            return True
        return False