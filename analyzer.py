import os
from typing import DefaultDict, List, Tuple, Set, Dict
from collections import defaultdict
from tqdm import tqdm
from tree_sitter import Tree
import numpy as np
import logging

from scope_strategy.base_strategy import BaseStrategy

from code_analyzer.schemas.function_info import FuncInfo
from code_analyzer.visitors.func_visitor import FunctionDefVisitor, LocalVarVisitor, LocalFunctionRefVisitor
from code_analyzer.visitors.global_visitor import GlobalVisitor, GlobalFunctionRefVisitor
from code_analyzer.definition_collector import BaseInfoCollector

from icall_analyzer.signature_match.matcher import TypeAnalyzer
from icall_analyzer.llm.base_analyzer import BaseLLMAnalyzer, GPTAnalyzer


def evaluate(targets: Dict[str, Set[str]], ground_truths: Dict[str, Set[str]]):
    logging.debug("start evaluating")
    precs = [] # 查准率
    recalls = [] # 召回率
    F1s = []
    count = 0
    for icall_key, labeled_funcs in tqdm(ground_truths.items(), desc="evaluating"):
        analyzed_targets: Set[str] = targets.get(icall_key, set())
        TPs: Set[str] = analyzed_targets & labeled_funcs
        if len(TPs) == 0:
            logging.debug("file containing missed: {}".format(icall_key))
            precs.append(0)
            recalls.append(0)
            F1s.append(0)
            count += 1
            continue
        prec = len(TPs) / len(analyzed_targets)
        recall = len(TPs) / len(labeled_funcs)
        precs.append(prec)
        recalls.append(recall)
        if recall < 1:
            logging.debug("file have missing: {}".format(icall_key))
            logging.debug("missed functions are: {}".format(labeled_funcs - TPs))
        if prec + recall == 0:
            F1s.append(0)
        else:
            F1s.append(2 * prec * recall / (prec + recall))

    P = np.mean(precs)
    R = np.mean(recalls)
    F1 = np.mean(F1s)
    logging.debug(f"{count} examples didn't produce valid analyze results")

    return (P, R, F1)

def extract_all_c_files(root: str, c_h_files: List):
    suffix_set = {"c", "h", "cc", "hh", "cpp", "hpp"}
    for root, dirs, files in os.walk(root):
        for file in files:
            suffixs = file.split(".")
            if len(suffixs) > 1 and suffixs[-1] in suffix_set:
                c_h_files.append(os.path.join(root, file))
    return c_h_files

def load_icall_infos(path: str) -> Tuple[DefaultDict[str, List[Tuple[int, int]]],
                                    DefaultDict[str, Set[str]]]:
    raw_infos = [line.strip() for line in open(path, 'r', encoding='utf-8').readlines()]
    # 将filename映射到该file下的每一个indirect-call，用line，col标识
    icall_dict: DefaultDict[str, List[Tuple[int, int]]] = defaultdict(list)
    # 将icall-key映射为groundtruth中的函数名，icall-key为filename:line:col
    ground_truths: DefaultDict[str, Set[str]] = defaultdict(set)
    for line in raw_infos:
        icall_key, funcs = line.split('|')
        # process icall_key
        res = icall_key.split(':')
        file = res[0]
        line = int(res[1]) - 1
        col = int(res[2]) - 1
        icall_dict[file].append((line, col))
        # process func infos
        func_keys = set(funcs.split(','))
        func_keys = {"<".join(func_key.split('<')[:2]) for func_key in func_keys}
        # process ground truths
        ground_truths[icall_key].update(func_keys)
    return icall_dict, ground_truths


def evaluate(targets: Dict[str, Set[str]], ground_truths: Dict[str, Set[str]]):
    logging.debug("start evaluating")
    precs = [] # 查准率
    recalls = [] # 召回率
    F1s = []
    count = 0
    for icall_key, labeled_funcs in tqdm(ground_truths.items(), desc="evaluating"):
        analyzed_targets: Set[str] = targets.get(icall_key, set())
        TPs: Set[str] = analyzed_targets & labeled_funcs
        if len(TPs) == 0:
            logging.debug("file containing missed: {}".format(icall_key))
            precs.append(0)
            recalls.append(0)
            F1s.append(0)
            count += 1
            continue
        prec = len(TPs) / len(analyzed_targets)
        recall = len(TPs) / len(labeled_funcs)
        precs.append(prec)
        recalls.append(recall)
        if recall < 1:
            logging.debug("file have missing: {}".format(icall_key))
            logging.debug("missed functions are: {}".format(labeled_funcs - TPs))
        if prec + recall == 0:
            F1s.append(0)
        else:
            F1s.append(2 * prec * recall / (prec + recall))

    P = np.mean(precs)
    R = np.mean(recalls)
    F1 = np.mean(F1s)
    logging.debug(f"{count} examples didn't produce valid analyze results")

    return (P, R, F1)

def evaluate_binary(ground_truths: Dict[str, Set[str]],
                    icall_sig_matcher_targets: Dict[str, Set[str]],
                    fp_dict: Dict[str, Set[str]]):
    TP = 0
    TN = 0
    FP = 0
    FN = 0
    fps: Dict[str, Set[str]] = {}
    fns: Dict[str, Set[str]] = {}
    for callsite_key in ground_truths.keys():
        if callsite_key not in icall_sig_matcher_targets.keys():
            continue
        matched_func_keys: Set[str] = icall_sig_matcher_targets[callsite_key]

        label_t_keys = matched_func_keys & ground_truths[callsite_key]
        label_f_keys = matched_func_keys - ground_truths[callsite_key]
        predicted_f_keys = fp_dict.get(callsite_key, set())
        predicted_t_keys = matched_func_keys - predicted_f_keys
        fp_set = label_f_keys & predicted_t_keys
        fn_set = label_t_keys & predicted_f_keys
        TP += len(label_t_keys & predicted_t_keys)
        TN += len(label_f_keys & predicted_f_keys)
        FP += len(label_f_keys & predicted_t_keys)
        FN += len(label_t_keys & predicted_f_keys)

        if len(fp_set) > 0:
            fps[callsite_key] = fp_set
        if len(fn_set) > 0:
            fns[callsite_key] = fn_set

    recall = TP / (TP + FN) if (TP + FN) > 0 else 0
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    F1 = 2 * recall * precision / (recall + precision) if (recall + precision) > 0 else 0

    return (precision, recall, F1, fps, fns)


class ProjectAnalyzer:
    def __init__(self, project_included_func_file: str, icall_infos_file: str, project_root: str,
                 args, project: str, model_name: str
                 ):
        if not (os.path.exists(project_included_func_file)
                and os.path.exists(icall_infos_file)
                    and os.path.exists(project_root)):
            logging.info("function name file or indirect-call ground truth or project root path missing")
            return
        self.included_funcs: Set[str] = set([line.strip() for line in
                                        open(project_included_func_file, 'r', encoding='utf-8').readlines()])
        infos: Tuple[defaultdict, defaultdict] = load_icall_infos(icall_infos_file)
        self.icall_dict: DefaultDict[str, List[Tuple[int, int]]] = infos[0]
        self.ground_truths: DefaultDict[str, Set[str]] = infos[1]
        self.project_root: str = project_root
        self.args = args
        self.project: str = project
        self.model_name = model_name

    def analyze_c_files_sig_match(self):
        c_h_files = []
        extract_all_c_files(self.project_root, c_h_files)
        funcdef_visitor = FunctionDefVisitor()
        global_visitor = GlobalVisitor()
        from code_analyzer.config import parser

        parsed_tree: List[Tree] = list()
        for file in tqdm(c_h_files, desc="parsing source files into trees"):
            relative_path = file[len(self.project_root) + 1:]
            logging.debug(relative_path)
            code: bytes = open(file, 'rb').read()
            tree: Tree = parser.parse(code)
            funcdef_visitor.current_file = relative_path
            funcdef_visitor.walk(tree)
            global_visitor.current_file = relative_path
            global_visitor.walk(tree)
            parsed_tree.append(tree)

        # 第二次扫描文件，统计每个函数global范围内被引用的函数
        global_ref_func_visitor = GlobalFunctionRefVisitor(set(funcdef_visitor.func_name_sets))
        for tree in parsed_tree:
            global_ref_func_visitor.walk(tree)
        refered_func_names: Set[str] = global_ref_func_visitor.refered_func
        func_set: Set[str] = global_ref_func_visitor.func_name_set
        logging.info("function name set has {} functions.".format(len(func_set)))

        func_key_2_name: Dict[str, str] = dict()
        func_key_2_declarator: Dict[str, str] = dict()
        func_info_dict: Dict[str, FuncInfo] = funcdef_visitor.func_info_dict

        # 第一次逐函数扫描，统计每个函数的局部变量定义和被引用的函数
        for func_key, func_info in tqdm(func_info_dict.items(), desc="parsing function infos"):
            local_var_visitor = LocalVarVisitor()
            local_var_visitor.traverse_node(func_info.func_body)
            # 支持可变参数的函数指针局部变量
            if len(local_var_visitor.local_var_param_var_arg) > 0:
                func_info.set_var_arg_func_var(local_var_visitor.local_var_param_var_arg)
            local_vars: Set[str] = set(local_var_visitor.local_var_infos.keys())
            func_info.set_local_var_info(local_var_visitor.local_var_infos)
            if len(local_var_visitor.func_var2param_types) > 0:
                func_info.set_func_var2param_types(local_var_visitor.func_var2param_types)
            arg_names: Set[str] = set([param[1] for param in func_info.parameter_types])
            local_func_ref_visitor = LocalFunctionRefVisitor(func_set, local_vars,
                                                             arg_names, refered_func_names)
            local_func_ref_visitor.traverse_node(func_info.func_body)
            func_info.set_local_var2declarator(local_var_visitor.local_var_2_declarator_text)
            func_key_2_name[func_key] = func_info.func_name
            func_key_2_declarator[func_key] = func_info.raw_declarator_text

        # 开始签名匹配
        if self.args.scope_strategy == "base":
            scope_strategy = BaseStrategy()
        else:
            scope_strategy = None

        # 收集必要信息，包括：
        # -
        collector: BaseInfoCollector = BaseInfoCollector(self.icall_dict, refered_func_names,
                                                         func_info_dict, global_visitor,
                                                         func_key_2_declarator)
        collector.build_all()
        llm_analyzer: BaseLLMAnalyzer = None
        if self.args.llm == "gpt":
            llm_analyzer = GPTAnalyzer(self.model_name, self.args.key)
        type_analyzer: TypeAnalyzer = TypeAnalyzer(collector, scope_strategy, llm_analyzer,
                                                   self.args.log_llm_output, self.project)
        type_analyzer.process_all()
        return type_analyzer

    def evaluate(self):
        type_analyzer = self.analyze_c_files_sig_match()
        logging.info("result of project, Precision, Recall, F1 is:")
        icall_2_targets: Dict[str, Set[str]] = type_analyzer.callees
        P, R, F1 = evaluate(icall_2_targets, self.ground_truths)
        logging.info(f"| {self.project} "
                        f"| {(P * 100):.1f} | {(R * 100):.1f} | {(F1 * 100):.1f} |")