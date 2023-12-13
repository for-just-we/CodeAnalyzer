import os
from typing import DefaultDict, List, Tuple, Set, Dict
from collections import defaultdict
from tqdm import tqdm
from tree_sitter import Tree
import numpy as np
import logging

from scope_strategy.base_strategy import BaseStrategy

from code_analyzer.preprocessor.node_processor import processor
from code_analyzer.schemas.ast_node import ASTNode
from code_analyzer.schemas.function_info import FuncInfo
from code_analyzer.visitors.func_visitor import FunctionDefVisitor, LocalVarVisitor, LocalFunctionRefVisitor
from code_analyzer.visitors.global_visitor import GlobalVisitor, GlobalFunctionRefVisitor
from code_analyzer.definition_collector import BaseInfoCollector

from icall_analyzer.signature_match.matcher import TypeAnalyzer
from icall_analyzer.llm.base_analyzer import BaseLLMAnalyzer, GPTAnalyzer

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


def print_added_true_positive(ground_truths: Dict[str, Set[str]],
                    predicted_t_keys_4_callsites: Dict[str, Set[str]]
                    ):
    for callsite_key in ground_truths.keys():
        label_t_keys: Set[str] = ground_truths.get(callsite_key, set())
        predicted_t_keys: Set[str] = predicted_t_keys_4_callsites.get(callsite_key, set())

        TPs: Set[str] = label_t_keys & predicted_t_keys
        if len(TPs) > 0:
            logging.debug("added true positive callsite: {}|{}".format(callsite_key, ",".join(TPs)))

    for callsite_key in ground_truths.keys():
        label_t_keys: Set[str] = ground_truths.get(callsite_key, set())
        predicted_t_keys: Set[str] = predicted_t_keys_4_callsites.get(callsite_key, set())
        FPs: Set[str] = predicted_t_keys - label_t_keys
        if len(FPs) > 0:
            logging.debug("added false positive callsite: {}|{}".format(callsite_key, ",".join(FPs)))


def evaluate_binary(ground_truths: Dict[str, Set[str]],
                    predicted_t_keys_4_callsites: Dict[str, Set[str]],
                    total_targets: Dict[str, Set[str]]):
    TP = 0
    TN = 0
    FP = 0
    FN = 0
    for callsite_key in ground_truths.keys():
        label_t_keys: Set[str] = ground_truths.get(callsite_key, set())
        label_f_keys: Set[str] = total_targets.get(callsite_key, set()) - label_t_keys
        predicted_t_keys: Set[str] = predicted_t_keys_4_callsites.get(callsite_key, set())
        predicted_f_keys: Set[str] = total_targets.get(callsite_key, set())\
                                     - predicted_t_keys

        TPs: Set[str] = label_t_keys & predicted_t_keys
        TNs: Set[str] = label_f_keys & predicted_f_keys
        FPs: Set[str] = label_f_keys & predicted_t_keys
        FNs: Set[str] = label_t_keys & predicted_f_keys

        TP += len(TPs)
        TN += len(TNs)
        FP += len(FPs)
        FN += len(FNs)

    acc = (TP + TN) / (TP + TN + FP + FN) if (TP + TN + FP + FN) > 0 else 0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    F1 = 2 * recall * precision / (recall + precision) if (recall + precision) > 0 else 0
    fpr = FP / (FP + TN) if (FP + TN) > 0 else 0
    fnr = FN / (FN + TP) if (FN + TP) > 0 else 0
    return (acc, precision, recall, F1, fpr, fnr)


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

        parsed_trees: List[ASTNode] = list()
        for file in tqdm(c_h_files, desc="parsing source files into trees"):
            relative_path = file[len(self.project_root) + 1:]
            logging.debug(relative_path)
            code: bytes = open(file, 'rb').read()
            tree: Tree = parser.parse(code)
            root_node: ASTNode = processor.visit(tree.root_node)
            funcdef_visitor.current_file = relative_path
            funcdef_visitor.traverse_node(root_node)
            global_visitor.current_file = relative_path
            global_visitor.traverse_node(root_node)
            parsed_trees.append(root_node)

        # 第二次扫描文件，统计每个函数global范围内被引用的函数
        global_ref_func_visitor = GlobalFunctionRefVisitor(set(funcdef_visitor.func_name_sets),
                                                           global_visitor.macro_defs)
        for root_node in parsed_trees:
            global_ref_func_visitor.traverse_node(root_node)
        refered_func_names: Set[str] = global_ref_func_visitor.refered_func
        func_set: Set[str] = global_ref_func_visitor.func_name_set
        logging.info("function name set has {} functions.".format(len(func_set)))

        func_key_2_name: Dict[str, str] = dict()
        func_key_2_declarator: Dict[str, str] = dict()
        func_info_dict: Dict[str, FuncInfo] = funcdef_visitor.func_info_dict

        # 第一次逐函数扫描，统计每个函数的局部变量定义和被引用的函数
        for func_key, func_info in tqdm(func_info_dict.items(), desc="parsing function infos"):
            local_var_visitor = LocalVarVisitor(global_visitor)
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
                                                             arg_names, refered_func_names,
                                                             global_visitor.macro_defs)
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
            llm_analyzer = GPTAnalyzer(self.model_name, self.args.key, self.args.temperature)
        type_analyzer: TypeAnalyzer = TypeAnalyzer(collector, self.args, scope_strategy,
                                                   llm_analyzer, self.project)
        type_analyzer.process_all()
        logging.debug("macro callsite num: {}".format(len(type_analyzer.macro_callsites)))
        logging.debug("macro callsites: {}".format("\n".join(type_analyzer.macro_callsites)))
        return type_analyzer

    def evaluate(self):
        type_analyzer = self.analyze_c_files_sig_match()
        logging.info("result of project, Precision, Recall, F1 is:")
        icall_2_targets: Dict[str, Set[str]] = type_analyzer.callees.copy()
        P, R, F1 = evaluate(icall_2_targets, self.ground_truths)
        logging.info(f"| {self.project} "
                        f"| {(P * 100):.1f} | {(R * 100):.1f} | {(F1 * 100):.1f} |")
        if self.args.log_res_to_file:
            open("result.txt", "a").write(f"| {self.project} | {(P * 100):.1f} | {(R * 100):.1f} | {(F1 * 100):.1f} |\n")

        def evaluate_icall_target(new_icall_2_target: Dict[str, Set[str]], info: str):
            icall_2_targets1 = icall_2_targets.copy()
            for key, values in new_icall_2_target.items():
                icall_2_targets1[key] = icall_2_targets1.get(key, set()) | values
            P, R, F1 = evaluate(icall_2_targets1, self.ground_truths)
            logging.info(f"| {self.project}-{info} "
                         f"| {(P * 100):.1f} | {(R * 100):.1f} | {(F1 * 100):.1f} |")
            if self.args.log_res_to_file:
                open("result.txt", "a").write(
                    f"| {self.project}-{info} | {(P * 100):.1f} | {(R * 100):.1f} | {(F1 * 100):.1f} |\n")

        def analyze_binary(all_potential_targets: Dict[str, Set[str]],
                           all_ground_truths: Dict[str, Set[str]],
                           analyzed_res: Dict[str, Set[str]], info: str):
            partial_ground_truth: Dict[str, Set[str]] = {key: all_ground_truths[key] &
                                                          all_potential_targets.get(key, set()) for key in
                                                     all_ground_truths.keys()}
            acc, prec, recall, F1, fpr, fnr = \
                evaluate_binary(partial_ground_truth, analyzed_res,
                                all_potential_targets)
            logging.info(f"| {self.project}-{info} "
                         f"| {(acc * 100):.1f} | {(prec * 100):.1f} | {(recall * 100):.1f} "
                         f"| {(F1 * 100):.1f} | {(fpr * 100):.1f} | {(fnr * 100):.1f} |")

        if self.args.count_uncertain:
            evaluate_icall_target(type_analyzer.uncertain_callees, "UC")
            analyze_binary(type_analyzer.uncertain_callees, self.ground_truths,
                           type_analyzer.uncertain_callees, "UC-yes")
            analyze_binary(type_analyzer.uncertain_callees, self.ground_truths,
                           dict(), "UC-no")

        if self.args.count_cast and self.args.enable_cast:
            evaluate_icall_target(type_analyzer.cast_callees, "Cast")
            analyze_binary(type_analyzer.cast_callees, self.ground_truths,
                           type_analyzer.cast_callees, "Cast-yes")
            analyze_binary(type_analyzer.cast_callees, self.ground_truths,
                           dict(), "Cast-no")

        if self.args.log_res_to_file:
            open("result.txt", "a").write(
                f"| ---- | ---- | ---- | ---- |\n")

        if self.args.evaluate_soly_for_llm:
            evaluate_icall_target(type_analyzer.llm_declarator_analysis, self.args.model_type)
            analyze_binary(type_analyzer.uncertain_callees, self.ground_truths,
                           type_analyzer.llm_declarator_analysis, self.args.model_type)

        if type_analyzer.llm_analyzer is not None and \
            hasattr("input_token_num", type_analyzer.llm_analyzer) and \
                hasattr("output_token_num", type_analyzer.llm_analyzer):
            logging.info("spent {} input tokens and {} output tokens for {}:".format(type_analyzer.llm_analyzer.input_token_num,
                                                                                    type_analyzer.llm_analyzer.output_token_num,
                                                                                    type_analyzer.llm_analyzer.model_type))