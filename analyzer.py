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
from code_analyzer.visitors.base_func_visitor import FunctionDefVisitor, LocalVarVisitor, LocalFunctionRefVisitor
from code_analyzer.visitors.func_body_visitors import EscapeTypeVisitor
from code_analyzer.visitors.global_visitor import GlobalVisitor, GlobalFunctionRefVisitor
from code_analyzer.definition_collector import BaseInfoCollector
from code_analyzer.utils.addr_taken_sites_util import extract_addr_site, AddrTakenSiteRetriver

from icall_solvers.base_solvers.base_matcher import BaseStaticMatcher
from icall_solvers.base_solvers.flta.matcher import TypeAnalyzer
from icall_solvers.base_solvers.mlta.type_confine_analyzer import TypeConfineAnalyzer
from icall_solvers.base_solvers.mlta.matcher import StructTypeMatcher
from icall_solvers.base_solvers.kelp.confine_func_analyzer import ConfineFuncAnalyzer
from icall_solvers.base_solvers.kelp.matcher import Kelp

from icall_solvers.llm_solvers.base_llm_solver import BaseLLMSolver
from icall_solvers.llm_solvers.semantic_match.matcher import SemanticMatcher
from icall_solvers.llm_solvers.single_step_match.matcher import SingleStepMatcher
from icall_solvers.llm_solvers.addr_site_v1.matcher import AddrSiteMatcherV1
from icall_solvers.llm_solvers.addr_site_v2.matcher import AddrSiteMatcherV2

from llm_utils.base_analyzer import BaseLLMAnalyzer

def extract_all_c_files(root: str, c_h_files: List):
    suffix_set = {"c", "h", "cc", "hh", "cpp", "hpp"}
    for root, dirs, files in os.walk(root):
        for file in files:
            suffixs = file.split(".")
            if len(suffixs) > 1 and suffixs[-1] in suffix_set:
                c_h_files.append(os.path.join(root, file))
    return c_h_files

def load_icall_infos(path: str) -> Tuple[DefaultDict[str, List[Tuple[int, int]]],
                                    DefaultDict[str, Set[str]],
                                    Dict[str, int]]:
    raw_infos = [line.strip() for line in open(path, 'r', encoding='utf-8').readlines()]
    # 将filename映射到该file下的每一个indirect-call，用line，col标识
    icall_dict: DefaultDict[str, List[Tuple[int, int]]] = defaultdict(list)
    # 将icall-key映射为groundtruth中的函数名，icall-key为filename:line:col
    ground_truths: DefaultDict[str, Set[str]] = defaultdict(set)
    # 将每个callsite映射到对应的索引号
    callsite_idxs: Dict[str, int] = dict()

    for idx, line in enumerate(raw_infos):
        items = line.split('|')
        if len(items) == 1:
            icall_key = items[0]
            funcs = ""
        else:
            icall_key, funcs = items
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
        callsite_idxs[icall_key] = idx
    return icall_dict, ground_truths, callsite_idxs

def evaluate(targets: Dict[str, Set[str]], ground_truths: Dict[str, Set[str]],
             enable_analysis_for_macro: bool,
             macro_callsites: Set[str]
             ):
    logging.getLogger("CodeAnalyzer").debug("start evaluating")
    precs = [] # 查准率
    recalls = [] # 召回率
    F1s = []
    count = 0
    for icall_key, labeled_funcs in tqdm(ground_truths.items(), desc="evaluating"):
        # 如果是macro callsite但是不计算macro callsite结果
        if icall_key in macro_callsites and not enable_analysis_for_macro:
            continue
        if len(labeled_funcs) == 0:
            continue
        analyzed_targets: Set[str] = targets.get(icall_key, set())
        TPs: Set[str] = analyzed_targets & labeled_funcs
        if len(TPs) == 0:
            logging.getLogger("CodeAnalyzer").debug("file containing missed: {}".format(icall_key))
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
            logging.getLogger("CodeAnalyzer").debug("file have missing: {}".format(icall_key))
            logging.getLogger("CodeAnalyzer").debug("missed functions are: {}".format(labeled_funcs - TPs))
        if prec + recall == 0:
            F1s.append(0)
        else:
            F1s.append(2 * prec * recall / (prec + recall))

    P = np.mean(precs)
    R = np.mean(recalls)
    F1 = np.mean(F1s)
    logging.getLogger("CodeAnalyzer").debug(f"{count} examples didn't produce valid analyze results")
    return (P, R, F1)


def evaluate_binary(ground_truths: Dict[str, Set[str]],
                    predicted_t_keys_4_callsites: Dict[str, Set[str]],
                    total_targets: Dict[str, Set[str]],
                    enable_analysis_for_macro: bool,
                    macro_callsites: Set[str]
                    ):
    TP = 0
    TN = 0
    FP = 0
    FN = 0
    for callsite_key in ground_truths.keys():
        # 如果是macro callsite但是不计算macro callsite结果
        if callsite_key in macro_callsites and not enable_analysis_for_macro:
            continue
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

def count_cost(input_token_num, output_token_num, input_price, output_price):
    return (input_token_num * input_price + output_token_num * output_price) / 1000

prices = {
    "gpt-3.5-turbo": [0.001, 0.002],
    "gpt-4-1106-preview": [0.01, 0.03],
    "gpt-4": [0.03, 0.06],

    "gemini-pro": [0.001, 0.002],
    "text-bison-001": [0.001, 0.002],
    "chat-bison-001": [0.001, 0.002],

    "glm-4": [0.1, 0.1],
    "glm-3-turbo ": [0.005, 0.005],

    "qwen-turbo": [0.008, 0.008],
    "qwen-plus": [0.02, 0.02]
}

class ProjectAnalyzer:
    def __init__(self, project_included_func_file: str, icall_infos_file: str, project_root: str,
                 args, project: str, model_name: str):
        if not (os.path.exists(project_included_func_file)
                and os.path.exists(icall_infos_file)
                    and os.path.exists(project_root)):
            logging.getLogger("CodeAnalyzer").info("function name file or indirect-call ground truth or project root path missing")
            return
        self.included_funcs: Set[str] = set([line.strip() for line in
                                        open(project_included_func_file, 'r', encoding='utf-8').readlines()])
        infos: Tuple[defaultdict, defaultdict, dict] = load_icall_infos(icall_infos_file)
        self.icall_dict: DefaultDict[str, List[Tuple[int, int]]] = infos[0]
        self.ground_truths: DefaultDict[str, Set[str]] = infos[1]
        self.callsite_idxs: Dict[str, int] = infos[2]
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
        for file in tqdm(c_h_files, desc="parsing source files into trees", ncols=self.args.ncols):
            relative_path = file[len(self.project_root) + 1:]
            logging.getLogger("CodeAnalyzer").debug(relative_path)
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
        logging.getLogger("CodeAnalyzer").info("function name set has {} functions.".format(len(func_set)))

        func_key_2_name: Dict[str, str] = dict()
        func_key_2_declarator: Dict[str, str] = dict()
        func_info_dict: Dict[str, FuncInfo] = funcdef_visitor.func_info_dict

        local_refer_sites_per_func_key: DefaultDict[str, DefaultDict[str, List[ASTNode]]] = \
            defaultdict(lambda: defaultdict(list))

        # 第一次逐函数扫描，统计每个函数的局部变量定义和被引用的函数
        for func_key, func_info in tqdm(func_info_dict.items(), desc="parsing function infos", ncols=self.args.ncols):
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

            for func_name, refer_sites in local_func_ref_visitor.local_refer_sites.items():
                local_refer_sites_per_func_key[func_name][func_key].extend(refer_sites)

        raw_global_addr_sites: Dict[str, List[ASTNode]] = \
            extract_addr_site(global_ref_func_visitor.global_refer_sites)
        raw_local_addr_sites: Dict[str, Dict[str, List[ASTNode]]] = dict()
        for func_name, local_refer_sites in local_refer_sites_per_func_key.items():
            raw_local_addr_sites[func_name] = extract_addr_site(local_refer_sites)


        # 开始签名匹配
        if self.args.scope_strategy == "base":
            scope_strategy = BaseStrategy()
            if self.args.only_count_scope:
                for callsite_key, targets in self.ground_truths.items():
                    targets = set(filter(lambda func_key:
                                         scope_strategy.analyze_key(callsite_key, func_key), targets))
                    self.ground_truths[callsite_key] = targets
        else:
            scope_strategy = None

        # 收集必要信息，包括：
        # -
        collector: BaseInfoCollector = BaseInfoCollector(func_set, self.icall_dict, refered_func_names,
                                                         func_info_dict, global_visitor,
                                                         func_key_2_declarator,
                                                         self.args.enable_analysis_for_macro)
        collector.build_all()

        return self.analyze_infos(collector, scope_strategy, raw_global_addr_sites,
                                  raw_local_addr_sites, func_key_2_name)



    def analyze_infos(self, collector: BaseInfoCollector, scope_strategy,
                      raw_global_addr_sites: Dict[str, List[ASTNode]],
                      raw_local_addr_sites: Dict[str, Dict[str, List[ASTNode]]],
                      func_key_2_name: Dict[str, str]
                      ) -> Tuple[BaseStaticMatcher, BaseLLMSolver]:
        llm_analyzer: BaseLLMAnalyzer = None
        if self.args.llm == "gpt":
            from llm_utils.openai_analyzer import OpenAIAnalyzer
            llm_analyzer = OpenAIAnalyzer(self.model_name, self.args.key, "",
                                          self.args.temperature)

        elif self.args.llm == "google":
            from llm_utils.google_analyzer import GoogleAnalyzer
            llm_analyzer = GoogleAnalyzer(self.model_name, self.args.key, self.args.temperature)
        elif self.args.llm == "zhipu":
            from llm_utils.zhipu_analyzer import ZhipuAnalyzer
            # refer to: https://github.com/THUDM/ChatGLM3/blob/main/openai_api_demo/zhipu_api_request.py#L17C34-L17C38
            llm_analyzer = ZhipuAnalyzer(self.model_name, self.args.key, self.args.address, self.args.temperature)

        elif self.args.llm == "tongyi":
            from llm_utils.tongyi_analyzer import TongyiAnalyzer
            llm_analyzer = TongyiAnalyzer(self.model_name, self.args.key, self.args.temperature)

        elif self.args.llm == "hf":
            from llm_utils.hf_analyzer import HuggingFaceAnalyzer
            llm_analyzer = HuggingFaceAnalyzer(self.model_name, self.args.address,
                                               self.args.temperature, self.args.max_new_tokens)

        elif self.args.llm == "openai_local":
            from llm_utils.openai_analyzer import OpenAIAnalyzer
            server_type = self.args.server_type
            llm_analyzer = OpenAIAnalyzer(self.model_name, "", self.args.address,
                                          self.args.temperature, self.args.max_tokens, server_type,
                                          add_llama3_stop=self.args.add_llama3_stop)

        type_analyzer: TypeAnalyzer = TypeAnalyzer(collector, self.args, scope_strategy,
                                                   llm_analyzer, self.project, self.callsite_idxs)
        type_analyzer.process_all()
        logging.getLogger("CodeAnalyzer").debug("macro callsite num: {}".format(len(type_analyzer.macro_callsites)))
        logging.getLogger("CodeAnalyzer").debug("macro callsites: {}".format("\n".join(type_analyzer.macro_callsites)))
        base_analyzer: BaseStaticMatcher = type_analyzer

        # 确定base_analyzer
        if self.args.base_analyzer in {"mlta", "kelp"}:
            type_confine_analyzer = TypeConfineAnalyzer(collector, raw_global_addr_sites, raw_local_addr_sites)
            type_confine_analyzer.analyze()

            # 进行escape分析
            escaped_types: DefaultDict[str, Set[str]] = defaultdict(set)
            for func_key, func_info in tqdm(collector.func_info_dict.items(), desc="type escape analysis for mlta", ncols=self.args.ncols):
                arg_info: Dict[str, str] = {parameter_type[1]: parameter_type[0]
                                            for parameter_type in func_info.parameter_types}
                escape_visitor = EscapeTypeVisitor(arg_info, func_info.name_2_declarator_text,
                                                   func_info.local_var, func_info.local_var2declarator, collector,
                                                   escaped_types)
                escape_visitor.traverse_node(func_info.func_body)

            struct_matcher = StructTypeMatcher(collector, self.args, type_analyzer,
                                              type_confine_analyzer, self.callsite_idxs, escaped_types)
            struct_matcher.process_all()

            base_analyzer = struct_matcher

            if self.args.base_analyzer == "kelp":
                confine_func_analyzer = ConfineFuncAnalyzer(collector,
                                                            raw_global_addr_sites,
                                                            raw_local_addr_sites)
                confine_func_analyzer.analyze()
                kelp_matcher = Kelp(self.args, collector, struct_matcher, confine_func_analyzer, self.callsite_idxs)
                kelp_matcher.process_all()
                base_analyzer = kelp_matcher


        # 筛选icall_solver
        llm_solver: BaseLLMSolver = None
        if self.args.llm_strategy == "semantic":
            llm_solver = SemanticMatcher(collector, self.args,
                                       base_analyzer, llm_analyzer, self.project, self.callsite_idxs,
                                       func_key_2_name)
            llm_solver.process_all()

        elif self.args.llm_strategy == "single":
            llm_solver = SingleStepMatcher(collector, self.args,
                                         base_analyzer, llm_analyzer, set(self.ground_truths.keys()),
                                         self.project, self.callsite_idxs,
                                         func_key_2_name)
            llm_solver.process_all()


        elif self.args.llm_strategy == "addr_site_v1":
            addr_taken_site_retriver = AddrTakenSiteRetriver(raw_global_addr_sites,
                                                             raw_local_addr_sites, collector)
            llm_solver = AddrSiteMatcherV1(collector, self.args, base_analyzer,
                                         addr_taken_site_retriver, llm_analyzer,
                                         self.project, self.callsite_idxs, func_key_2_name)
            llm_solver.process_all()

        elif self.args.llm_strategy == "addr_site_v2":
            addr_taken_site_retriver = AddrTakenSiteRetriver(raw_global_addr_sites,
                                                             raw_local_addr_sites, collector)
            addr_taken_site_retriver.group()
            llm_solver = AddrSiteMatcherV2(collector, self.args, base_analyzer,
                                         addr_taken_site_retriver, llm_analyzer,
                                         self.project, self.callsite_idxs, func_key_2_name)
            llm_solver.process_all()

        return base_analyzer, llm_solver


    def evaluate(self):
        base_analyzer, llm_solver = self.analyze_c_files_sig_match()
        # 只进行类型分析
        if self.args.llm_strategy == "none":
            P, R, F1 = self.evaluate_base_analysis(base_analyzer)
        # 进行语义匹配
        else:
            P, R, F1 = self.evaluate_semantic_analysis(llm_solver)

        items = self.evaluate_(llm_solver, base_analyzer)
        return items, (P, R, F1)

    def evaluate_base_analysis(self, base_analyzer: BaseStaticMatcher):
        logging.getLogger("CodeAnalyzer").info("result of project, Precision, Recall, F1 is:")
        icall_2_targets: Dict[str, Set[str]] = base_analyzer.callees.copy()

        P, R, F1 = evaluate(icall_2_targets, self.ground_truths, self.args.enable_analysis_for_macro,
                            base_analyzer.macro_callsites)

        logging.getLogger("CodeAnalyzer").info(f"| {self.project} "
                     f"| {(P * 100):.1f} | {(R * 100):.1f} | {(F1 * 100):.1f} |")
        line = f"{(P * 100):.1f},{(R * 100):.1f},{(F1 * 100):.1f}"
        line1 = ""

        if self.args.log_total_info:
            additional = "{},{},{},{}\n"
            flta_info = len(base_analyzer.flta_cases) if hasattr(base_analyzer, "flta_cases") else ""
            mlta_info = len(base_analyzer.mlta_cases) if hasattr(base_analyzer, "mlta_cases") else ""
            kelp_info = len(base_analyzer.kelp_cases) if hasattr(base_analyzer, "kelp_cases") else ""
            additional_info = additional.format(self.project, flta_info, mlta_info, kelp_info)
            open("total.txt", 'a', encoding='utf-8').write(additional_info)

        def evaluate_icall_target(new_icall_2_target: Dict[str, Set[str]], info: str):
            icall_2_targets1 = icall_2_targets.copy()
            for key, values in new_icall_2_target.items():
                icall_2_targets1[key] = icall_2_targets1.get(key, set()) | values
            P, R, F1 = evaluate(icall_2_targets1, self.ground_truths, self.args.enable_analysis_for_macro,
                                base_analyzer.macro_callsites)
            logging.getLogger("CodeAnalyzer").info(f"| {self.project}-{info} "
                         f"| {(P * 100):.1f} | {(R * 100):.1f} | {(F1 * 100):.1f} |")
            line = f"{self.project}-{info},{(P * 100):.1f},{(R * 100):.1f},{(F1 * 100):.1f}"
            return P, R, F1


        def analyze_binary(all_potential_targets: Dict[str, Set[str]],
                           all_ground_truths: Dict[str, Set[str]],
                           analyzed_res: Dict[str, Set[str]], info: str):
            partial_ground_truth: Dict[str, Set[str]] = {key: all_ground_truths[key] &
                                                              all_potential_targets.get(key, set()) for key in
                                                         all_ground_truths.keys()}
            acc, prec, recall, F1, fpr, fnr = \
                evaluate_binary(partial_ground_truth, analyzed_res,
                                all_potential_targets, self.args.enable_analysis_for_macro,
                                base_analyzer.macro_callsites)
            logging.getLogger("CodeAnalyzer").info(f"| {self.project}-{info} "
                         f"| {(acc * 100):.1f} | {(prec * 100):.1f} | {(recall * 100):.1f} "
                         f"| {(F1 * 100):.1f} | {(fpr * 100):.1f} | {(fnr * 100):.1f} |")
            line1 = f"{self.project}-{info},{(acc * 100):.1f},{(prec * 100):.1f}," \
                    f"{(recall * 100):.1f},{(F1 * 100):.1f},{(fpr * 100):.1f},{(fnr * 100):.1f}"
            return line1


        if self.args.evaluate_uncertain:
            total_extra_callees = base_analyzer.uncertain_callees
            P, R, F1 = evaluate_icall_target(total_extra_callees, "TotalExtra")
            line = analyze_binary(total_extra_callees, self.ground_truths,
                           total_extra_callees, "TotalExtra-yes")
            line1 = analyze_binary(total_extra_callees, self.ground_truths,
                           dict(), "TotalExtra-no")

        if self.args.evaluate_soly_for_llm:
            P, R, F1 = evaluate_icall_target(base_analyzer.llm_declarator_analysis,
                                  self.args.model_type + '-' + str(self.args.temperature))
            line1 = analyze_binary(base_analyzer.uncertain_callees, self.ground_truths,
                           base_analyzer.llm_declarator_analysis,
                           self.args.model_type + '-' + str(self.args.temperature))


        if hasattr(base_analyzer, "llm_analyzer") and \
                base_analyzer.llm_analyzer is not None:
            price = prices.get(base_analyzer.llm_analyzer.model_type, [0, 0])
            cost = count_cost(base_analyzer.llm_analyzer.input_token_num,
                              base_analyzer.llm_analyzer.output_token_num,
                              price[0], price[1])
            logging.getLogger("CodeAnalyzer").info("spent {} input tokens and {} output tokens for {}: , cost: {:.2f}"
                         .format(base_analyzer.llm_analyzer.input_token_num,
                                 base_analyzer.llm_analyzer.output_token_num,
                                 base_analyzer.llm_analyzer.model_type,
                                 cost))
            logging.getLogger("CodeAnalyzer").info(
                "| {} | {} | {} | {} | {:.2f} |".format(self.project, base_analyzer.llm_analyzer.input_token_num,
                                                        base_analyzer.llm_analyzer.output_token_num,
                                                        base_analyzer.llm_analyzer.model_type, cost))

            line1 += f"\n{base_analyzer.llm_analyzer.input_token_num / 1000},{base_analyzer.llm_analyzer.output_token_num}"
            line1 += f"\n{base_analyzer.llm_analyzer.max_input_token_num},{base_analyzer.llm_analyzer.max_output_token_num},{base_analyzer.llm_analyzer.max_total_token_num}"

        if self.args.log_res_to_file and hasattr(base_analyzer, "log_dir"):
            logging.getLogger("CodeAnalyzer").info("writing result to evaluation_result.txt")
            assert hasattr(base_analyzer, "log_dir")
            info = self.args.base_analyzer
            if self.args.enable_semantic_for_mlta:
                info += "_seman"
            with open(f"{base_analyzer.log_dir}/evaluation_result_{info}.txt", "w", encoding='utf-8') as f:
                f.write(line + "\n" + line1)
                logging.getLogger("CodeAnalyzer").info("writing success")

        return P, R, F1

    def evaluate_semantic_analysis(self, llm_solver: BaseLLMSolver):
        icall_2_targets: Dict[str, Set[str]] = llm_solver.matched_callsites.copy()
        P, R, F = evaluate(icall_2_targets, self.ground_truths, self.args.enable_analysis_for_macro,
                           llm_solver.macro_callsites)

        if hasattr(llm_solver, "llm_analyzer"):
            model_name = llm_solver.llm_analyzer.model_name
            llm_analyzer: BaseLLMAnalyzer = llm_solver.llm_analyzer
        else:
            model_name = ""
            llm_analyzer = None
        logging.getLogger("CodeAnalyzer").info(f"| {self.project}-{model_name} "
                     f"| {(P * 100):.1f} | {(R * 100):.1f} | {(F * 100):.1f} |")
        line1 = f"{(P * 100):.1f},{(R * 100):.1f},{(F * 100):.1f}"

        acc, prec, recall, F1, fpr, fnr = \
            evaluate_binary(self.ground_truths, icall_2_targets,
                            llm_solver.type_matched_callsites, self.args.enable_analysis_for_macro,
                            llm_solver.macro_callsites)
        logging.getLogger("CodeAnalyzer").info(f"| {self.project}-{model_name} "
                     f"| {(acc * 100):.1f} | {(prec * 100):.1f} | {(recall * 100):.1f} "
                     f"| {(F1 * 100):.1f} | {(fpr * 100):.1f} | {(fnr * 100):.1f} |")
        line2 = f"{(acc * 100):.1f},{(prec * 100):.1f},{(recall * 100):.1f}," \
                        f"{(F1 * 100):.1f},{(fpr * 100):.1f},{(fnr * 100):.1f}"
        line = line1 + "\n" + line2

        if llm_analyzer is not None:
            price = prices.get(llm_analyzer.model_type, [0, 0])
            cost = count_cost(llm_analyzer.input_token_num, llm_analyzer.output_token_num,
                              price[0], price[1])
            logging.getLogger("CodeAnalyzer").info("spent {} input tokens and {} output tokens for {}: , cost: {:.2f}"
                         .format(llm_analyzer.input_token_num, llm_analyzer.output_token_num,
                                 llm_analyzer.model_type, cost))
            logging.getLogger("CodeAnalyzer").info(
                "| {} | {} | {} | {} | {:.2f} |".format(self.project, llm_analyzer.input_token_num,
                                llm_analyzer.output_token_num, llm_analyzer.model_type, cost))
            line3 = f"{llm_analyzer.input_token_num / 1000},{llm_analyzer.output_token_num / 1000},{llm_analyzer.model_type},{cost}"
            line4 = f"{llm_analyzer.max_input_token_num},{llm_analyzer.max_output_token_num},{llm_analyzer.max_total_token_num}"
            line = line + "\n" + line3 + "\n" + line4

        if self.args.log_res_to_file and hasattr(llm_solver, "log_dir"):
            logging.getLogger("CodeAnalyzer").info("writing result to evaluation_result.txt")
            info = self.args.base_analyzer
            if self.args.enable_semantic_for_mlta:
                info += "_seman"
            with open(f"{llm_solver.log_dir}/evaluation_result_{info}.txt", "w", encoding='utf-8') as f:
                f.write(line)
                logging.getLogger("CodeAnalyzer").info("writing success")

        return P, R, F

    def evaluate_(self, llm_solver: BaseLLMSolver,
                  base_analyzer: BaseStaticMatcher) -> Tuple[List[float], List[float], List[float],
                                                             List[float], List[float], List[float],
                                                             List[str], List[str], List[str],
                                                             List[int], List[int], List[int],
                                                             List[str], Set[str], List[str]]:
        if llm_solver is None or not hasattr(base_analyzer, "flta_cases"):
            return ([], [], [], [], [], [], [], [], [], [], [], [], [],
                    base_analyzer.analyzed_callsites, [])
        assert hasattr(base_analyzer, "flta_cases")

        # 基于类型匹配的结果
        type_matched_callsites: Dict[str, Set[str]] = base_analyzer.callees.copy()
        additional_callsite_infos: DefaultDict[str, Set[str]] = defaultdict(set)
        if self.args.evaluate_uncertain:
            additional_callsite_infos = base_analyzer.uncertain_callees
        elif self.args.evaluate_soly_for_llm:
            additional_callsite_infos = base_analyzer.llm_declarator_analysis
        for key, values in additional_callsite_infos.items():
            type_matched_callsites[key] = type_matched_callsites.get(key, set()) | values

        # 基于语义分析的结果
        matched_callsites: DefaultDict[str, Set[str]] = llm_solver.matched_callsites

        semantic_res_prec: List[float] = []
        semantic_res_recall: List[float] = []
        semantic_res_f1: List[float] = []

        flta_res_prec: List[float] = []
        flta_res_recall: List[float] = []
        flta_res_f1: List[float] = []

        failed_type_cases: List[str] = []
        success_type_cases: List[str] = []
        macro_cases: List[str] = []
        label_nums: List[int] = []
        flta_nums: List[int] = []
        seman_nums: List[int] = []

        local_failed_cases: List[str] = []
        global_failed_cases: List[str] = []
        for callsite_key in self.ground_truths.keys():
            if callsite_key not in base_analyzer.analyzed_callsites:
                global_failed_cases.append(callsite_key)

        def eval(analyzed_targets: Set[str], labeled_funcs: Set[str]):
            TPs: Set[str] = analyzed_targets & labeled_funcs
            prec = 0 if len(analyzed_targets) == 0 else len(TPs) / len(analyzed_targets)
            recall = 0 if len(labeled_funcs) == 0 else len(TPs) / len(labeled_funcs)
            f1 = 0 if prec + recall == 0 else 2 * prec * recall / (prec + recall)
            return prec, recall, f1

        for callsite_key, labeled_funcs in tqdm(self.ground_truths.items(),
                                                desc="evaluating for pure flta cases", ncols=self.args.ncols):
            if callsite_key in base_analyzer.macro_callsites:
                macro_cases.append(callsite_key)
            # 不是flta cases
            if not callsite_key in base_analyzer.flta_cases:
                continue
            # flta分析没有成功
            flta_funcs: Set[str] = type_matched_callsites.get(callsite_key, set())
            if len(flta_funcs) == 0:
                failed_type_cases.append(callsite_key)
                if callsite_key in base_analyzer.local_failed_callsites:
                    local_failed_cases.append(callsite_key)
                continue

            flta_prec, flta_recall, flta_f1 = eval(flta_funcs, labeled_funcs)
            if flta_recall == 0:
                failed_type_cases.append(callsite_key)
                continue
            flta_res_prec.append(flta_prec)
            flta_res_recall.append(flta_recall)
            flta_res_f1.append(flta_f1)

            semantic_res: Set[str] = matched_callsites.get(callsite_key, set())
            seman_prec, seman_recall, seman_f1 = eval(semantic_res, labeled_funcs)
            semantic_res_prec.append(seman_prec)
            semantic_res_recall.append(seman_recall)
            semantic_res_f1.append(seman_f1)

            success_type_cases.append(callsite_key)
            label_nums.append(len(labeled_funcs))
            flta_nums.append(len(flta_funcs))
            seman_nums.append(len(semantic_res))
            
        return (semantic_res_prec, semantic_res_recall, semantic_res_f1,
                flta_res_prec, flta_res_recall, flta_res_f1, failed_type_cases, success_type_cases,
                macro_cases, label_nums, flta_nums, seman_nums, local_failed_cases, base_analyzer.analyzed_callsites,
                global_failed_cases)