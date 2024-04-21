from icall_solvers.base_solvers.base_matcher import BaseStaticMatcher
from icall_solvers.base_solvers.mlta.matcher import StructTypeMatcher
from icall_solvers.base_solvers.kelp.confine_func_analyzer import ConfineFuncAnalyzer
from code_analyzer.visitors.util_visitor import ExprAnalyzer
from code_analyzer.definition_collector import BaseInfoCollector

from typing import Dict, DefaultDict, Set
from collections import defaultdict
from tqdm import tqdm

class Kelp(BaseStaticMatcher):
    def __init__(self, args,
                 collector: BaseInfoCollector,
                 struct_type_matcher: StructTypeMatcher,
                 confine_func_analyzer: ConfineFuncAnalyzer,
                 callsite_idxs: Dict[str, int] = None):
        super().__init__()
        self.collector = collector
        self.args = args
        self.struct_type_matcher = struct_type_matcher
        self.confine_func_analyzer = confine_func_analyzer
        self.callsite_idxs: Dict[str, int] = callsite_idxs

        self.confined_funcs: Set[str] = set()
        self.simple_icall_keys: Set[str] = set()
        self.simple_icall2func_names: DefaultDict[str, Set[str]] = defaultdict(set)
        self.icall_2_func = struct_type_matcher.icall_2_func
        self.icall_nodes = struct_type_matcher.icall_nodes
        self.macro_callsites: Set[str] = struct_type_matcher.macro_callsites
        self.analyzed_callsites.update(struct_type_matcher.analyzed_callsites)
        self.local_failed_callsites.update(struct_type_matcher.local_failed_callsites)

        if hasattr(struct_type_matcher, "log_dir"):
            self.log_dir = struct_type_matcher.log_dir

        self.analyze_simple_icalls(confine_func_analyzer)

        self.flta_cases: Set[str] = struct_type_matcher.flta_cases
        self.mlta_cases: Set[str] = struct_type_matcher.mlta_cases
        self.kelp_cases: Set[str] = set(self.simple_icall2func_names.keys())
        self.flta_cases = self.flta_cases - self.kelp_cases
        self.mlta_cases = self.mlta_cases - self.kelp_cases


    def analyze_simple_icalls(self, confine_func_analyzer: ConfineFuncAnalyzer):
        # 提取simple icall key
        for func_name, callsite_keys in confine_func_analyzer.func_name2icall_key.items():
            # 确认该func_name没有被赋值给complex global var
            global_vars: Set[str] = confine_func_analyzer.func_name2global_vars[func_name]
            flag = True
            for global_var in global_vars:
                if global_var in confine_func_analyzer.complex_df_globals:
                    # 存在complex global var被赋值
                    flag = False
                    break

            if not flag:
                continue

            self.confined_funcs.add(func_name)
            # 遍历所有被该func赋值过的indirect_callsite
            for callsite_key in callsite_keys:
                if callsite_key in self.callsite_idxs.keys():
                    self.simple_icall2func_names[callsite_key].add(func_name)

        # 遍历查找是否有全局结构体变量
        for callsite_key in self.callsite_idxs.keys():
            if callsite_key in self.simple_icall2func_names.keys():
                continue
            if callsite_key not in self.icall_nodes.keys():
                continue
            call_node = self.icall_nodes[callsite_key]
            callee_node = call_node.children[0]
            expr_visitor = ExprAnalyzer()
            expr_visitor.traverse_node(callee_node)

            # 如果是普通变量
            if len(expr_visitor.identifiers) == 0:
                continue
            var_name = expr_visitor.identifiers[0]
            # 首先不能是局部变量和函数参数
            func_key = self.icall_2_func[callsite_key]
            func_info = self.collector.func_info_dict[func_key]
            param_names: Set[str] = set([param[1] for param in func_info.parameter_types])
            local_vars: Set[str] = set(func_info.local_var.keys())
            if var_name not in (param_names | local_vars) and var_name in \
                    self.confine_func_analyzer.simple_df_globals:
                if len(expr_visitor.identifiers) == 1:
                    # 如果该全局变量是simple function pointer
                    if var_name in self.confine_func_analyzer.global_var2func.keys():
                        self.simple_icall2func_names[callsite_key].\
                            update(self.confine_func_analyzer.global_var2func[var_name])

                # 是结构体变量
                elif len(expr_visitor.identifiers) > 1:
                    identifiers: tuple = tuple(expr_visitor.identifiers)
                    if identifiers in self.confine_func_analyzer.global_var_field2func.keys():
                        self.simple_icall2func_names[callsite_key].update(
                            self.confine_func_analyzer.global_var_field2func[identifiers]
                        )


        for var_name, callsite_keys in self.confine_func_analyzer.global_var2affected_callsites.items():
            if var_name not in self.confine_func_analyzer.simple_df_globals:
                continue
            if var_name not in self.confine_func_analyzer.global_var2func.keys():
                continue
            for callsite_key in callsite_keys:
                if callsite_key in self.simple_icall2func_names.keys():
                    self.simple_icall2func_names[callsite_key].update(
                        self.confine_func_analyzer.global_var2func[var_name])


        # 遍历查找是否有simple function local variable
        for func_key, local_var_infos in self.confine_func_analyzer.simple_local_var2func.items():
            for local_var, func_names in local_var_infos.items():
                # 如果是simple var
                if local_var in self.confine_func_analyzer.simple_df_locals[func_key]:
                    for func_name in func_names:
                        if func_name not in self.confine_func_analyzer.complex_df_func_locals:
                            self.confined_funcs.add(func_name)

        # 遍历所有的callsite key，查找是否有引用局部变量的情况
        for callsite_key in self.callsite_idxs.keys():
            if callsite_key in self.simple_icall2func_names.keys():
                continue
            if callsite_key not in self.icall_nodes.keys():
                continue
            call_node = self.icall_nodes[callsite_key]
            callee_node = call_node.children[0]
            expr_visitor = ExprAnalyzer()
            expr_visitor.traverse_node(callee_node)

            # 如果是普通变量
            if len(expr_visitor.identifiers) == 0:
                continue
            var_name = expr_visitor.identifiers[0]
            # 首先不能是局部变量和函数参数
            func_key = self.icall_2_func[callsite_key]
            func_info = self.collector.func_info_dict[func_key]
            param_names: Set[str] = set([param[1] for param in func_info.parameter_types])
            local_vars: Set[str] = set(func_info.local_var.keys())
            # 如果是局部变量而且是simple function pointer
            if var_name in local_vars and var_name in self.confine_func_analyzer.simple_df_locals[func_key]:
                cur_target_funcs: Set[str] = self.confine_func_analyzer. \
                    simple_local_var2func[func_key][var_name]
                if len(cur_target_funcs) > 0:
                    self.simple_icall2func_names[callsite_key] = cur_target_funcs



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
        matcher_funcs = [
            (self.struct_type_matcher.callees[callsite_key], self.callees, "strict type"),
            (self.struct_type_matcher.uncertain_callees[callsite_key], self.uncertain_callees, "uncertain type"),
            (self.struct_type_matcher.llm_declarator_analysis[callsite_key], self.llm_declarator_analysis, "llm decided")
        ]
        # 如果是simple function pointer
        if callsite_key in self.simple_icall2func_names.keys():
            target_func_names: Set[str] = self.simple_icall2func_names[callsite_key]
            for matcher_func, callee_set, msg in matcher_funcs:
                for func_key in tqdm(matcher_func, desc="process for {} callees of callsite {}".format(msg, i)):
                    if self.confine_func_analyzer.collector.func_info_dict[func_key].func_name in target_func_names:
                        callee_set[callsite_key].add(func_key)

        # 如果不是，沿用mlta的结果，同时删除confined function
        else:
            for matcher_func, callee_set, msg in matcher_funcs:
                for func_key in tqdm(matcher_func, desc="process for {} callees of callsite {}".format(msg, i)):
                    if self.confine_func_analyzer.collector.func_info_dict[func_key].func_name in \
                            self.confined_funcs:
                        continue
                    callee_set[callsite_key].add(func_key)