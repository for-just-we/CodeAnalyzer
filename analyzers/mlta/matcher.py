from code_analyzer.definition_collector import BaseInfoCollector
from code_analyzer.schemas.ast_node import ASTNode

from analyzers.flta.matcher import TypeAnalyzer
from analyzers.mlta.init_info import InitInfo

from typing import Dict, Set, DefaultDict
from collections import defaultdict
from tqdm import tqdm

class StructTypeMatcher:
    def __init__(self, collector: BaseInfoCollector,
                 args,
                 type_analyzer: TypeAnalyzer,
                 init_info: InitInfo,
                 callsite_idxs: Dict[str, int] = None,
                 escaped_types: DefaultDict[str, Set[str]] = None):
        self.collector: BaseInfoCollector = collector
        self.args = args
        self.init_info: InitInfo = init_info
        self.escaped_types = escaped_types

        # 保存类型匹配的callsite
        self.type_matched_callsites: Dict[str, Set[str]] = type_analyzer.callees.copy()
        if args.count_uncertain:
            for key, values in type_analyzer.uncertain_callees.items():
                self.type_matched_callsites[key] = self.type_matched_callsites.get(key, set()) | values

        self.icall_2_func: Dict[str, str] = type_analyzer.icall_2_func
        self.icall_nodes: Dict[str, ASTNode] = type_analyzer.icall_nodes
        # 每一个indirect-call对应的函数指针声明的文本
        self.icall_2_decl_text: Dict[str, str] = type_analyzer.icall_2_decl_text
        # 每一个indirect-call对应的函数指针声明文本，保留原始类型
        self.icall_2_decl_type_text: Dict[str, str] = type_analyzer.icall_2_decl_type_text
        # 如果icall引用了结构体的field，找到对应的结构体名称
        self.icall_2_struct_name: Dict[str, str] = type_analyzer.icall_2_struct_name
        # 如果icall引用了结构体的field，找到对应的field_name
        self.icall_2_field_name: Dict[str, str] = type_analyzer.icall_2_field_name
        self.macro_callsites: Set[str] = type_analyzer.macro_callsites

        self.callsite_idxs: Dict[str, int] = callsite_idxs
        # 保存匹配结果
        self.matched_callsites: DefaultDict[str, Set[str]] = defaultdict(set)


    def process_all(self):
        # 遍历callsite
        for (callsite_key, func_keys) in self.type_matched_callsites.items():
            if callsite_key not in self.icall_2_func.keys():
                continue
            # 如果不分析macro call
            if callsite_key in self.macro_callsites and not self.args.enable_analysis_for_macro:
                continue
            # 如果不分析正常call
            elif callsite_key not in self.macro_callsites and self.args.disable_analysis_for_normal:
                continue

            i = self.callsite_idxs[callsite_key]
            self.process_callsite(callsite_key, i, func_keys)


    def process_callsite(self, callsite_key: str, i: int, func_keys: Set[str]):
        struct_name = self.icall_2_struct_name.get(callsite_key, "")
        field_name = self.icall_2_field_name.get(callsite_key, "")

        if struct_name != "" and field_name != "":
            # 是escape type
            if field_name in self.escaped_types[struct_name]:
                self.matched_callsites[callsite_key].update(func_keys)
                return
            func_names: Set[str] = self.init_info.struct_name_2_field_4_type[struct_name][field_name]
            for func_key in tqdm(func_keys, desc="match for callsite key: {}".format(i)):
                cur_func_name: str = self.collector.func_info_dict[func_key].func_name
                if cur_func_name in func_names:
                    self.matched_callsites[callsite_key].add(func_key)
            # 出现escape type
            if len(self.matched_callsites[callsite_key]) == 0:
                self.matched_callsites[callsite_key].update(func_keys)

        else:
            self.matched_callsites[callsite_key].update(func_keys)