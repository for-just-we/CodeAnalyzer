import logging

from code_analyzer.signature_match import ICallSigMatcher
from typing import Dict, Set, List, DefaultDict
from tree_sitter import Node
from tqdm import tqdm
from collections import defaultdict
import os

from llm_analyzer.llm_analyzers.base_analyzer import BaseLLMAnalyzer

# 读取已经分析过的callsite，避免重复分析
def extract_callsite_key(log_file: str):
    callsite_keys = set()
    for line in open(log_file, 'r', encoding='utf-8'):
        if line == '\n':
            continue
        callsite_key = line.split('|')[0]
        callsite_keys.add(callsite_key)
    return callsite_keys

class SimpleFilter:
    def __init__(self, local_var_2_declarator: Dict[str, Dict[str, str]],
                 arg_2_declarator: Dict[str, Dict[str, str]],
                 func_key_2_declarator: Dict[str, str],
                 func_key_2_name: Dict[str, str],
                 global_var_2_declarator: Dict[str, str],
                 icall_sig_matcher: ICallSigMatcher,
                 macro_2_content: Dict[str, str],
                 args,
                 project: str,
                 model_name: str):
        # 将func_key映射为variable name的declarator text
        self.local_var_2_declarator: Dict[str, Dict[str, str]] = local_var_2_declarator
        # 将func_key映射为arg的declarator text
        self.arg_2_declarator: Dict[str, Dict[str, str]] = arg_2_declarator
        self.func_key_2_declarator: Dict[str, str] = func_key_2_declarator
        self.global_var_2_declarator: Dict[str, str] = global_var_2_declarator
        self.project = project
        # 将indirect-callsite映射为function key集合
        # 不重复分析
        self.callees: Dict[str, Set[str]] = icall_sig_matcher.callees
        root_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        log_dir = f"{root_path}/experimental_logs/step2/{model_name}"
        if not os.path.exists(log_dir):
            os.mkdir(log_dir)
        self.log_file = f"{log_dir}/{self.project}.txt"
        if os.path.exists(self.log_file):
            callsite_keys = extract_callsite_key(self.log_file)
            self.callees = {key: value for key, value in self.callees.items()
                            if key not in callsite_keys}

        # 将indirect-callsite-key映射为callsite文本
        self.icall_node: Dict[str, Node] = icall_sig_matcher.icall_nodes
        # 将indirect-call映射到所在函数
        self.icall_2_func: Dict[str, str] = icall_sig_matcher.icall_2_func
        self.llm_analyzer: BaseLLMAnalyzer = None
        self.args = args
        self.func_key2_name: Dict[str, str] = func_key_2_name

        self.macro_2_content: Dict[str, str] = macro_2_content
        self.macro_icall2_callexpr: Dict[str, str] = icall_sig_matcher.macro_icall2_callexpr


    def extract_decl_context(self, callsite_key: str) -> List[str]:
        call_expr: Node = self.icall_node.get(callsite_key)
        identifiers: List[str] = list()
        self.extract_identifier_name(call_expr, identifiers)
        # 获取当前callsite所在function
        cur_func: str = self.icall_2_func.get(callsite_key)
        decl_contexts: List[str] = list()
        for identifier in identifiers:
            declarator = self.get_declarator_4_var(identifier, cur_func)
            if declarator is not None:
                decl_contexts.append(declarator)
        decl_contexts.append(call_expr.text.decode('utf8'))
        return decl_contexts

    def extract_identifier_name(self, node: Node, identifiers: List[str]):
        if node.type == "identifier":
            identifier = node.text.decode('utf8')
            if identifier not in identifiers:
                identifiers.append(identifier)
        for child in node.children:
            self.extract_identifier_name(child, identifiers)

    def get_declarator_4_var(self, identifier: str, cur_func: str):
        # 首先查找局部变量表，然后是形参列表，然后是全局变量表
        local_var_dict: Dict[str, str] = self.local_var_2_declarator.get(cur_func, dict())
        if identifier in local_var_dict:
            return local_var_dict[identifier]
        # 形参列表
        arg_dict: Dict[str, str] = self.arg_2_declarator.get(cur_func, dict())
        if identifier in arg_dict:
            return arg_dict[identifier]
        return self.global_var_2_declarator.get(identifier, None)

    def visit_all_callsites(self) -> DefaultDict[str, Set[str]]:
        total_callee_num = len(self.callees.keys())
        fp_dict: DefaultDict[str, Set[str]] = defaultdict(set)
        for i, callsite_key in enumerate(self.callees.keys()):
            logging.info("visiting {}/{} icall".format(i + 1, total_calrenamelee_num))
            fp_set: Set[str] = self.visit_callsite(callsite_key, i + 1, total_callee_num)
            fp_dict[callsite_key] = fp_set
            self.dump(callsite_key, fp_set)
        return fp_dict

    def visit_callsite(self, callsite_key: str, icall_idx, total_callee_num) -> Set[str]:
        flag: bool = callsite_key in self.macro_icall2_callexpr.keys()
        macro_content = ""
        if flag:
            macro = self.macro_icall2_callexpr[callsite_key]
            macro_content = self.macro_2_content[macro]
        callee_targets: Set[str] = self.callees[callsite_key]
        to_visit_targets: Set[str] = callee_targets.copy()
        fp_set: Set[str] = set()
        visited: Set[str] = set()
        unchanged: int = 0
        # callsite_text: str = self.icall_node[callsite_key].text.decode('utf8')
        declarator_context: List[str] = self.extract_decl_context(callsite_key)
        while len(to_visit_targets) > 0:
            # 剩下统统标记为uncertain
            if unchanged >= self.args.max_try_time:
                break
            pre_length = len(visited)
            group_target_key: Set[str] = set()
            group_func_name: Set[str] = set()
            group_func_name2key: Dict[str, str] = dict()
            count = 0
            for func_key in to_visit_targets:
                if count >= (self.args.func_num_per_batch * self.args.batch_size):
                    break
                func_name = self.func_key2_name[func_key]
                if func_name not in group_func_name:
                    group_func_name2key[func_name] = func_key
                    group_func_name.add(func_name)
                    group_target_key.add(func_key)
                    count += 1

            # 如果是宏函数调用
            if flag:
                batch_result: Dict[str, str] = self.visit_group_targets_4_macro_call(
                    declarator_context, group_target_key, macro_content
                )
            else:
                batch_result: Dict[str, str] = self.visit_group_targets(
                    declarator_context, group_target_key)
            for func_name, res in batch_result.items():
                visited.add(group_func_name2key[func_name])
                if res == "no":
                    fp_set.add(group_func_name2key[func_name])
            if len(visited) == pre_length:
                unchanged += 1
            else:
                unchanged = 0
            to_visit_targets = to_visit_targets - visited
            logging.debug("visiting {}/{} icall, callsite key: {}, remaining {} potential targets"
                          .format(icall_idx, total_callee_num, callsite_key, len(to_visit_targets)))
        return fp_set

    def visit_group_targets(self, declarator_context: List[str],
                            group_target_key: Set[str]) -> Dict[str, str]:
        func_declarators: Dict[str, str] = {self.func_key2_name[func_key] : self.func_key_2_declarator[func_key] for func_key
                                       in group_target_key}
        final_result: Dict[str, str] = self.llm_analyzer.analyze_function_declarators(
            declarator_context, func_declarators)
        return final_result


    def visit_group_targets_4_macro_call(self, declarator_context: List[str],
                                         group_target_key: Set[str],
                                         macro_content: str) -> Dict[str, str]:
        func_declarators: Dict[str, str] = {self.func_key2_name[func_key]: self.func_key_2_declarator[func_key] for
                                            func_key
                                            in group_target_key}
        final_result: Dict[str, str] = self.llm_analyzer.analyze_function_declarators_4_macro_call(
            declarator_context, func_declarators, macro_content
        )
        return final_result

    def dump(self, callsite_key: str, fp_set: Set[str]):
        file = open(self.log_file, 'a', encoding='utf-8')
        file.write(f"{callsite_key}|{','.join(fp_set)}\n")
        file.close()