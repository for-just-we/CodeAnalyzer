from typing import Dict, List, DefaultDict, Tuple, Set
from collections import defaultdict
from tqdm import tqdm

from code_analyzer.visit_utils.type_util import parsing_type, get_original_type
from code_analyzer.schemas.function_info import FuncInfo
from code_analyzer.visitors.global_visitor import GlobalVisitor

# 收集类型别名、结构体定义等信息
class BaseInfoCollector:
    def __init__(self, icall_dict: DefaultDict[str, List[Tuple[int, int]]],
                 refered_funcs: Set[str],
                 func_info_dict: Dict[str, FuncInfo],
                 global_visitor: GlobalVisitor):
        self.icall_dict: DefaultDict[str, List[Tuple[int, int]]] = icall_dict
        self.func_info_dict: Dict[str, FuncInfo] = func_info_dict
        self.type_alias_infos: Dict[str, str] = global_visitor.type_alias_infos
        # 全局变量
        self.global_var_info: Dict[str, str] = global_visitor.global_var_info
        # 结构体field信息
        self.struct_infos: DefaultDict[str, Dict[str, str]] = global_visitor.struct_infos
        # 将函数指针类型映射回原本定义
        self.func_type2raw_declarator: Dict[str, str] = global_visitor.func_type2raw_declarator
        # 将函数指针映射到相应类型序列
        self.func_type2param_types: Dict[str, List[str]] = global_visitor.func_type2param_types
        # 结构体函数指针field
        self.func_struct_fields: Dict[str, Dict[str, List[str]]] = \
                global_visitor.func_struct_fields
        self.func_struct_field_declarators: Dict[str, Dict[str, str]] = \
                global_visitor.func_struct_field_declarators

        # 函数指针全局变量
        if len(global_visitor.func_var2param_types):
            self.func_var2param_types: Dict[str, List[str]] = global_visitor.func_var2param_types
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

        # 初始函数集合
        self.refered_funcs: Set[str] = refered_funcs

        # 支持可变参数的函数指针类型、全局变量以及结构体field
        self.var_arg_func_types: Set[str] = global_visitor.var_param_func_type
        self.var_arg_func_vars: Set[str] = global_visitor.var_param_func_var
        self.var_arg_struct_fields: Dict[str, Set[str]] = \
            global_visitor.var_param_func_struct_fields

        # 结构体第一个field的类型
        self.struct_first_field_types: Dict[str, str] = \
            global_visitor.struct_first_field_types

    # 构建查询结构
    def build_basic_info(self):
        self.considered_funcs = set(filter(lambda func_key: self.func_info_dict[func_key].func_name
                                                                    in self.refered_funcs, self.func_info_dict.keys()))
        for func_key in tqdm(self.considered_funcs, desc="building busic parameter infos"):
            func_info = self.func_info_dict.get(func_key)
            # 处理可变参数函数
            if func_info.var_arg:
                self.var_arg_param_nums_2_func_keys[len(func_info.parameter_types)] \
                    .add(func_key)
            else:
                self.param_nums_2_func_keys[len(func_info.parameter_types)].add(func_key)

    def build_ori_param_types_4_funcs(self):
        for func_key, func_info in tqdm(self.func_info_dict.items(), desc="building original parameter infos"):
            types = []
            for param_type in func_info.parameter_types:
                src_type_name, pointer_level = parsing_type((param_type[0], 0))
                src_type: Tuple[str, int] = get_original_type((src_type_name, pointer_level),
                                                              self.type_alias_infos)
                types.append(src_type)
            self.param_types[func_key] = types

    def build_all(self):
        self.build_basic_info()
        self.build_ori_param_types_4_funcs()