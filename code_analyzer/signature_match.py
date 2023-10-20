from typing import Dict, List, DefaultDict, Tuple, Set
from collections import defaultdict
from tqdm import tqdm
import logging
from tree_sitter import Node

from code_analyzer.visit_utils.base_util import loc_inside
from code_analyzer.visit_utils.type_util import parsing_type, get_original_type
from code_analyzer.schemas.function_info import FuncInfo
from code_analyzer.visitors.func_visitor import FunctionBodyVisitor
from code_analyzer.visitors.global_visitor import GlobalVisitor

from scope_strategy.base_strategy import BaseStrategy

# 完成Step 1
class ICallSigMatcher:
    def __init__(self, icall_dict: DefaultDict[str, List[Tuple[int, int]]],
                 refered_funcs: Set[str],
                 func_info_dict: Dict[str, FuncInfo],
                 global_visitor: GlobalVisitor,
                 only_refered: bool = False, hard_match: bool = False,
                 scope_strategy: BaseStrategy = None):
        self.icall_dict: DefaultDict[str, List[Tuple[int, int]]] = icall_dict
        self.func_info_dict: Dict[str, FuncInfo] = func_info_dict
        self.type_alias_infos: Dict[str, str] = global_visitor.type_alias_infos
        # 全局变量
        self.global_var_info: Dict[str, str] = global_visitor.global_var_info
        # 结构体field信息
        self.struct_infos: DefaultDict[str, Dict[str, str]] = global_visitor.struct_infos
        # 包含的enum定义
        self.enum_infos: Set[str] = global_visitor.enum_infos
        # 宏函数
        self.macro_funcs: Set[str] = set(global_visitor.macro_func_bodies.keys())

        # 参数数量对应的函数名
        self.param_nums_2_func_keys: DefaultDict[int, Set[str]] = defaultdict(set)
        # 可变参数类型的参数数量对应函数名
        self.var_arg_param_nums_2_func_keys: DefaultDict[int, Set[str]] = defaultdict(set)
        # 保存每个函数修正后的参数类型
        self.param_types: Dict[str, List[Tuple[str, int]]] = dict()

        # 保存匹配上的函数名
        self.callees: Dict[str, Set[str]] = dict()
        # 将宏函数间接调用点映射为宏名称
        self.macro_icall2_callexpr: Dict[str, str] = dict()

        # hard_match为false匹配规则会相对宽松，void* 和 char* 类指针可以和任意指针类型匹配
        self.hard_match: bool = hard_match
        self.refered_funcs: Set[str] = refered_funcs
        self.only_refered: bool = only_refered

        # 保存每个indirect-callsite的代码文本
        self.icall_nodes: Dict[str, Node] = dict()
        # 保存每个indirect-callsite所在的function
        self.icall_2_func: Dict[str, str] = dict()
        # scope策略
        self.scope_strategy: BaseStrategy = scope_strategy

    # 构建查询结构
    def build_basic_info(self):
        self.considered_funcs: Set[str] = set(self.func_info_dict.keys())
        if self.only_refered:
            self.considered_funcs = set(filter(lambda func_key: self.func_info_dict[func_key].func_name
                                          in self.refered_funcs, self.considered_funcs))
        for func_key in tqdm(self.considered_funcs, desc="building busic parameter infos"):
            func_info = self.func_info_dict.get(func_key)
            # 处理可变参数函数
            if func_info.var_arg:
                self.var_arg_param_nums_2_func_keys[len(func_info.parameter_types)]\
                    .add(func_key)
            else:
                self.param_nums_2_func_keys[len(func_info.parameter_types)].add(func_key)

    def process_all(self):
        # 遍历每个函数
        for func_key, func_info in tqdm(self.func_info_dict.items(), desc="processing functions"):
            icall_locs: List[Tuple[int, int]] = self.icall_dict.get(
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
            icall_locs, self.global_var_info, arg_info, self.type_alias_infos,
            self.struct_infos, func_info.local_var, self.macro_funcs)
        func_body_visitor.traverse_node(func_info.func_body)
        for icall_loc in icall_locs:
            callsite_key: str = f"{func_info.file}:{icall_loc[0] + 1}:{icall_loc[1] + 1}"
            if icall_loc not in func_body_visitor.icall_nodes.keys():
                self.callees[callsite_key] = set()
                continue
            self.icall_nodes[callsite_key] = func_body_visitor.icall_nodes[icall_loc]
            self.icall_2_func[callsite_key] = func_key
            # 当前调用为宏函数，考虑所有的函数
            if icall_loc in func_body_visitor.current_macro_funcs.keys():
                considered_func_keys = self.considered_funcs
                if self.scope_strategy is not None:
                    considered_func_keys = set(filter(lambda func_key:
                                               self.scope_strategy.analyze_key(callsite_key, func_key),
                                               considered_func_keys))
                self.callees[callsite_key] = considered_func_keys
                self.macro_icall2_callexpr[callsite_key] = func_body_visitor.current_macro_funcs[icall_loc]
                continue
            arg_type: List[Tuple[str, int]] = \
                func_body_visitor.arg_info_4_callsite.get(icall_loc)
            if arg_type is None:
                logging.debug("error parsing indirect-callsite: {}".format(callsite_key))
                continue
            self.match_4_indirect_call(arg_type, callsite_key)



    # 根据形参签名匹配indirect-call对应的潜在callee
    def match_4_indirect_call(self, arg_type: List[Tuple[str, int]], callsite_key: str):
        # 参数数量
        arg_num: int = len(arg_type)
        fixed_arg_type: List[Tuple[str, int]] = list()
        for arg_t in arg_type:
            src_type, pointer_level = parsing_type(arg_t)
            fixed_arg_type.append(get_original_type((src_type, pointer_level),
                                                    self.type_alias_infos))
        func_set: Set[str] = set()

        def process_func_set(func_keys: Set[str],
                             cur_fixed_arg_type: List[Tuple[str, int]]):
            new_func_keys = func_keys.copy()
            if self.scope_strategy is not None:
                new_func_keys = set(filter(lambda func_key:
                                           self.scope_strategy.analyze_key(callsite_key, func_key),
                                           new_func_keys))
            if not self.hard_match:
                func_set.update(new_func_keys)
            else:
                for func_key in new_func_keys:
                    # 函数形参类型
                    param_types: List[Tuple[str, int]] = self.param_types.get(func_key)
                    flag = self.match_types(cur_fixed_arg_type, param_types)
                    # 如果匹配成功
                    if flag:
                        func_set.add(func_key)

        # 遍历固定参数数量的函数列表
        fixed_num_func_keys: Set[str] = self.param_nums_2_func_keys.get(arg_num, {})
        process_func_set(fixed_num_func_keys, fixed_arg_type)

        # 遍历可变参数函数列表
        for param_num, func_keys in self.var_arg_param_nums_2_func_keys.items():
            # 可能被调用
            if param_num <= arg_num:
                process_func_set(func_keys, fixed_arg_type[: param_num])

        self.callees[callsite_key] = func_set

    def build_ori_param_types_4_funcs(self):
        for func_key, func_info in tqdm(self.func_info_dict.items(), desc="building original parameter infos"):
            types = []
            for param_type in func_info.parameter_types:
                src_type_name, pointer_level = parsing_type((param_type[0], 0))
                src_type: Tuple[str, int] = get_original_type((src_type_name, pointer_level),
                                                              self.type_alias_infos)
                types.append(src_type)
            self.param_types[func_key] = types

    # 匹配callsite实参类型arg_types和callee形参类型param_types
    def match_types(self, arg_types: List[Tuple[str, int]],
                    param_types: List[Tuple[str, int]]) -> bool:
        assert len(arg_types) == len(param_types)
        # 逐个参数匹配
        for i in range(len(arg_types)):
            arg_type: Tuple[str, int] = arg_types[i]
            param_type: Tuple[str, int] = param_types[i]

            # 确认二者都是结构体的情况下比较类型
            if arg_type[0] in self.struct_infos.keys() and \
                param_type[0] in self.struct_infos.keys():
                return arg_type[0] == param_type[0] and arg_type[1] == param_type[1]
            # 如果二者都是枚举类型，判断是不是同一种枚举
            elif arg_type[0] in self.enum_infos and \
                param_type[0] in self.enum_infos:
                return arg_type[0] == param_type[0] and arg_type[1] == param_type[1]
            else:
                return True

    # 匹配callsite实参类型arg_types和callee形参类型param_types
    # def match_types(self, arg_types: List[Tuple[str, int]],
    #                 param_types: List[Tuple[str, int]]) -> bool:
    #     assert len(arg_types) == len(param_types)
    #     # 逐个参数匹配
    #     for i in range(len(arg_types)):
    #         arg_type: Tuple[str, int] = arg_types[i]
    #         param_type: Tuple[str, int] = param_types[i]
    #         # 如果其中一个类型未知，那么认为匹配成功
    #         if arg_type[0] == TypeEnum.UnknownType.value or \
    #                 param_type[0] == TypeEnum.UnknownType.value:
    #             continue
    #         # 如果二者都是函数指针类型，那么不区分什么类型的函数一律匹配成功
    #         elif arg_type[0] == TypeEnum.FunctionType.value and \
    #                 param_type[0] == TypeEnum.FunctionType.value:
    #             continue
    #         # 如果类型名和pointer level都匹配的上
    #         elif arg_type[0] == param_type[0] and \
    #                 arg_type[1] == param_type[1]:
    #             continue
    #         # 都不属于结构体类型，原生类型一律认为可以隐式cast
    #         elif arg_type[0] not in self.struct_infos.keys() \
    #             and param_type[0] not in self.struct_infos.keys():
    #             continue
    #         # void*可以和任意指针类型匹配，包括多级指针
    #         # 这里如果二者都是指针类型并且其中一个是void类型的指针，则可以匹配
    #         elif (arg_type[1] > 0 and param_type[1] > 0)\
    #             and (arg_type[0] == "void" or param_type[0] == "void"):
    #             continue
    #         else:
    #             return False
    #     return True