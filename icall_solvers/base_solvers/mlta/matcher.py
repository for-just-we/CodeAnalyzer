from code_analyzer.definition_collector import BaseInfoCollector

from icall_solvers.base_solvers.base_matcher import BaseStaticMatcher
from icall_solvers.base_solvers.flta.matcher import TypeAnalyzer
from icall_solvers.base_solvers.mlta.type_confine_analyzer import TypeConfineAnalyzer

from typing import Dict, Set, DefaultDict
from tqdm import tqdm

class StructTypeMatcher(BaseStaticMatcher):
    def __init__(self, collector: BaseInfoCollector,
                 args,
                 type_analyzer: TypeAnalyzer,
                 confine_analyzer: TypeConfineAnalyzer,
                 callsite_idxs: Dict[str, int] = None,
                 escaped_types: DefaultDict[str, Set[str]] = None):
        super().__init__()
        self.collector: BaseInfoCollector = collector
        self.args = args
        self.confine_analyzer: TypeConfineAnalyzer = confine_analyzer
        self.escaped_types = escaped_types

        # 保存类型匹配的callsite
        self.type_analyzer = type_analyzer
        self.icall_2_func = type_analyzer.icall_2_func
        self.uncertain_idxs.update(type_analyzer.uncertain_idxs)

        self.icall_2_field_name: Dict[str, str] = type_analyzer.icall_2_field_name
        self.callsite_idxs: Dict[str, int] = callsite_idxs

        # 如果icall引用了结构体的field，找到对应的结构体名称
        self.icall_2_struct_name: Dict[str, str] = type_analyzer.icall_2_struct_name
        # 如果icall引用了结构体的field，找到对应的field_name
        self.icall_2_field_name: Dict[str, str] = type_analyzer.icall_2_field_name
        self.macro_callsites: Set[str] = type_analyzer.macro_callsites
        self.icall_nodes = type_analyzer.icall_nodes

        if hasattr(type_analyzer, "log_dir"):
            self.log_dir = type_analyzer.log_dir


    def process_all(self):
        # 遍历callsite
        for callsite_key, i in self.callsite_idxs.items():
            if callsite_key not in self.icall_2_func.keys():
                continue
            # 如果不分析macro call
            if callsite_key in self.macro_callsites and not self.args.enable_analysis_for_macro:
                continue
            # 如果不分析正常call
            elif callsite_key not in self.macro_callsites and self.args.disable_analysis_for_normal:
                continue

            self.process_callsite(callsite_key, i)


    def process_callsite(self, callsite_key: str, i: int):
        struct_name = self.icall_2_struct_name.get(callsite_key, "")
        field_name = self.icall_2_field_name.get(callsite_key, "")

        strict_type_targets: Set[str] = self.type_analyzer.callees[callsite_key].copy()
        uncertain_targets: Set[str] = self.type_analyzer.uncertain_callees[callsite_key].copy()
        llm_decl_targets: Set[str] = self.type_analyzer.llm_declarator_analysis[callsite_key].copy()

        if struct_name != "" and field_name != "":
            # 是escape type
            if field_name in self.escaped_types[struct_name]:
                self.update_default_values(callsite_key, strict_type_targets, uncertain_targets, llm_decl_targets)
                return
            func_names: Set[str] = self.confine_analyzer.struct_name_2_field_4_type[struct_name][field_name]

            for field_name, target_set in [("callees", strict_type_targets),
                               ("uncertain_callees", uncertain_targets),
                               ("llm_declarator_analysis", llm_decl_targets)]:
                for func_key in tqdm(target_set, desc=f"match for {field_name} callsite key: {i}"):
                    cur_func_name = self.collector.func_info_dict[func_key].func_name
                    if cur_func_name in func_names:
                        getattr(self, field_name)[callsite_key].add(func_key)

            # 出现escape type
            if len((self.callees[callsite_key] | self.uncertain_callees[callsite_key])) == 0:
                self.update_default_values(callsite_key, strict_type_targets, uncertain_targets, llm_decl_targets)

        else:
            self.update_default_values(callsite_key, strict_type_targets, uncertain_targets, llm_decl_targets)

    # Add a helper method to simplify code further

    def update_default_values(self, callsite_key: str, strict_type_targets: Set[str],
                              uncertain_targets: Set[str], llm_decl_targets: Set[str]):
        self.callees[callsite_key] = strict_type_targets
        self.uncertain_callees[callsite_key] = uncertain_targets
        self.llm_declarator_analysis[callsite_key] = llm_decl_targets