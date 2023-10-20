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
            logging.info("visiting {}/{} icall".format(i + 1, total_callee_num))
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
        fp_set: Set[str] = set()
        # callsite_text: str = self.icall_node[callsite_key].text.decode('utf8')
        declarator_context: List[str] = self.extract_decl_context(callsite_key)
        for func_key in tqdm(callee_targets, desc="analayzing indirect-call for {}-th icall"
                                                  ", total {} icalls".format(icall_idx, total_callee_num)):
            if func_key not in self.func_key_2_declarator.keys():
                continue
            func_name = self.func_key2_name[func_key]
            func_declarator = self.func_key_2_declarator[func_key]
            # 如果是宏函数调用
            if flag:
                ans: bool = self.llm_analyzer.analyze_function_declarators_4_macro_call(
                    declarator_context, func_name, func_declarator, macro_content)
            else:
                ans: bool = self.llm_analyzer.analyze_function_declarator(
                    declarator_context, func_name, func_declarator)
            if not ans:
                fp_set.add(func_key)

        return fp_set


    def dump(self, callsite_key: str, fp_set: Set[str]):
        file = open(self.log_file, 'a', encoding='utf-8')
        file.write(f"{callsite_key}|{','.join(fp_set)}\n")
        file.close()