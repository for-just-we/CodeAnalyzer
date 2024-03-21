import time

from code_analyzer.definition_collector import BaseInfoCollector
from code_analyzer.schemas.ast_node import ASTNode
from code_analyzer.schemas.function_info import FuncInfo

from llm_utils.common_prompt import summarizing_prompt, summarizing_prompt_4_model
from llm_utils.base_analyzer import BaseLLMAnalyzer
from analyzers.flta.matcher import TypeAnalyzer
from analyzers.single_step_match.prompt import System_Match, User_Match, User_Match_macro, supplement_prompts

from tqdm import tqdm
import os
import logging
from typing import Dict, Set, DefaultDict, List
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class SingleStepMatcher:
    def __init__(self, collector: BaseInfoCollector,
                 args,
                 type_analyzer: TypeAnalyzer,
                 llm_analyzer: BaseLLMAnalyzer = None,
                 callsite_keys: Set[str] = None,
                 project="",
                 callsite_idxs: Dict[str, int] = None,
                 func_key_2_name: Dict[str, str] = None):
        self.collector: BaseInfoCollector = collector
        # 是否采用二段式prompt
        self.double_prompt: bool = args.double_prompt
        self.args = args
        self.callsite_keys: Set[str] = callsite_keys.copy()
        self.callsite_idxs: Dict[str, int] = callsite_idxs

        self.icall_2_func: Dict[str, str] = type_analyzer.icall_2_func
        self.icall_nodes: Dict[str, ASTNode] = type_analyzer.icall_nodes
        self.macro_callsites: Set[str] = type_analyzer.macro_callsites

        self.expanded_macros: Dict[str, str] = type_analyzer.expanded_macros
        self.macro_call_exprs: Dict[str, str] = type_analyzer.macro_call_exprs

        # 严格类型匹配成功的callsite
        self.strict_type_matched_callsites: Dict[str, Set[str]] = type_analyzer.callees
        # 通过cast分析得到类型匹配成功的callsite
        self.cast_type_matched_callsites: Dict[str, Set[str]] = type_analyzer.cast_callees
        # 包含在uncertain部分的callsite
        self.uncertain_type_matched_callsites: Dict[str, Set[str]] = type_analyzer.uncertain_callees

        self.type_matched_callsites: Dict[str, Set[str]] = dict()
        for callsite_key in self.callsite_keys:
            func_keys: Set[str] = set()
            func_keys.update(self.strict_type_matched_callsites.get(callsite_key, set()))
            func_keys.update(self.cast_type_matched_callsites.get(callsite_key, set()))
            func_keys.update(self.uncertain_type_matched_callsites.get(callsite_key, set()))
            self.type_matched_callsites[callsite_key] = func_keys

        # 保存语义匹配的callsite
        self.matched_callsites: DefaultDict[str, Set[str]] = defaultdict(set)
        self.llm_analyzer: BaseLLMAnalyzer = llm_analyzer

        self.func_key_2_name: Dict[str, str] = func_key_2_name

        # log的位置
        self.log_flag: bool = args.log_llm_output
        if self.log_flag:
            root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
            epoch_sig: str = str(self.args.running_epoch)
            if self.args.double_prompt:
                epoch_sig += "-double"
            self.log_dir = f"{root_path}/experimental_logs/single_step_analysis/{epoch_sig}/{self.llm_analyzer.model_name}/" \
                           f"{project}"
            self.res_log_file = f"{self.log_dir}/single_step_result.txt"
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir)


    def process_all(self):
        logging.getLogger("CodeAnalyzer").info("Start single step matching...")

        if self.args.load_pre_single_step_analysis_res:
            assert os.path.exists(self.res_log_file)
            logging.getLogger("CodeAnalyzer").info("loading existed single step matching results.")
            with open(self.res_log_file, "r", encoding='utf-8') as f:
                for line in f:
                    tokens: List[str] = line.strip().split('|')
                    callsite_key: str = tokens[0]
                    func_keys: Set[str] = set()
                    if len(tokens) > 1:
                        func_keys.update(tokens[1].split(','))
                    func_keys = set(filter(lambda func_key:
                                           self.func_key_2_name.get(func_key, '') in self.collector.refered_funcs,
                                           func_keys))
                    self.matched_callsites[callsite_key] = func_keys
            return

        logging.getLogger("CodeAnalyzer").info("should analyzing {} icalls".format(len(self.callsite_keys)))

        if os.path.exists(self.res_log_file):
            logging.getLogger("CodeAnalyzer").info("loading existed semantic matching results automatically")
            with open(self.res_log_file, "r", encoding='utf-8') as f:
                for line in f:
                    tokens: List[str] = line.strip().split('|')
                    callsite_key: str = tokens[0]
                    func_keys: Set[str] = set()
                    if len(tokens) > 1:
                        func_keys.update(tokens[1].split(','))
                    self.matched_callsites[callsite_key] = func_keys
                    self.callsite_keys.remove(callsite_key)

        logging.getLogger("CodeAnalyzer").info("remaining {} icalls to be analyzed".format(len(self.callsite_keys)))
        time.sleep(2)

        for callsite_key in self.callsite_keys:
            if callsite_key not in self.icall_2_func.keys():
                continue
            i: int = self.callsite_idxs[callsite_key]
            if callsite_key in self.macro_callsites and self.args.disable_analysis_for_macro:
                continue
            elif callsite_key not in self.macro_callsites and self.args.disable_analysis_for_normal:
                continue
            # 首先找出该callsite所在function
            if callsite_key in self.macro_callsites:
                self.process_macro_callsite(callsite_key, i)
            else:
                self.process_normal_callsite(callsite_key, i)

            # 如果log，记录下分析结果
            if self.log_flag:
                func_keys: Set[str] = self.matched_callsites[callsite_key]
                content: str = callsite_key + "|" + ",".join(func_keys) + "\n"
                with open(self.res_log_file, "a", encoding='utf-8') as f:
                    f.write(content)

    def process_normal_callsite(self, callsite_key: str, i: int):
        # 首先找出该callsite所在function
        parent_func_key: str = self.icall_2_func[callsite_key]
        parent_func_info: FuncInfo = self.collector.func_info_dict[parent_func_key]
        src_func_name: str = parent_func_info.func_name
        src_func_text: str = parent_func_info.func_def_text
        callsite_text: str = self.icall_nodes[callsite_key].node_text

        cur_log_dir = f"{self.log_dir}/callsite-{i}"
        target_analyze_log_dir = f"{cur_log_dir}/single"
        # 如果需要log
        if self.log_flag:
            if not os.path.exists(target_analyze_log_dir):
                os.makedirs(target_analyze_log_dir)

        def analyze_callsite_type_matching(callsite_key, callsite_text, src_func_name, src_func_text,
                                           target_analyze_log_dir, match_type):
            matched_func_keys: Set[str] = getattr(self, f"{match_type}_type_matched_callsites", {}).get(
                callsite_key, set())

            lock = threading.Lock()
            executor = ThreadPoolExecutor(max_workers=self.args.num_worker)
            pbar = tqdm(total=len(matched_func_keys),
                        desc=f"single step matching for {match_type} type matched callsite-{i}: {callsite_key}")
            futures = []

            def update_progress(future):
                pbar.update(1)

            def worker(func_key: str, idx: int):
                flag = self.process_callsite_target(callsite_text, src_func_name, src_func_text,
                                                    target_analyze_log_dir, func_key, idx, match_type)
                if flag:
                    with lock:
                        self.matched_callsites[callsite_key].add(func_key)

            for idx, func_key in enumerate(matched_func_keys):
                future = executor.submit(worker, func_key, idx)
                future.add_done_callback(update_progress)
                futures.append(future)

            for future in as_completed(futures):
                future.result()

        # 严格类型匹配
        analyze_callsite_type_matching(callsite_key, callsite_text, src_func_name, src_func_text,
                                       target_analyze_log_dir, "strict")

        # Cast类型匹配
        analyze_callsite_type_matching(callsite_key, callsite_text, src_func_name, src_func_text,
                                       target_analyze_log_dir, "cast")

        # Uncertain类型匹配
        analyze_callsite_type_matching(callsite_key, callsite_text, src_func_name, src_func_text,
                                       target_analyze_log_dir, "uncertain")


    def process_macro_callsite(self, callsite_key: str, i: int):
        # 首先找出该callsite所在function
        parent_func_key: str = self.icall_2_func[callsite_key]
        parent_func_info: FuncInfo = self.collector.func_info_dict[parent_func_key]
        src_func_name: str = parent_func_info.func_name
        src_func_text: str = parent_func_info.func_def_text
        callsite_text: str = self.icall_nodes[callsite_key].node_text
        expanded_macro: str = self.expanded_macros[callsite_key]
        macro_call_expr: str = self.macro_call_exprs[callsite_key]

        cur_log_dir = f"{self.log_dir}/callsite-{i}"
        target_analyze_log_dir = f"{cur_log_dir}/single"
        # 如果需要log
        if self.log_flag:
            if not os.path.exists(target_analyze_log_dir):
                os.makedirs(target_analyze_log_dir)

        def analyze_callsite_type_matching(match_type):
            matched_func_keys: Set[str] = getattr(self, f"{match_type}_type_matched_callsites", {}).get(
                callsite_key, set())

            lock = threading.Lock()
            executor = ThreadPoolExecutor(max_workers=self.args.num_worker)
            pbar = tqdm(total=len(matched_func_keys),
                        desc=f"single step matching for {match_type} type matched callsite-{i}: {callsite_key}")
            futures = []

            def update_progress(future):
                pbar.update(1)

            def worker(func_key: str, idx: int):
                flag = self.process_macro_callsite_target(callsite_text, expanded_macro, macro_call_expr, src_func_name, src_func_text,
                                                    target_analyze_log_dir, func_key, idx, match_type)
                if flag:
                    with lock:
                        self.matched_callsites[callsite_key].add(func_key)

            for idx, func_key in enumerate(matched_func_keys):
                future = executor.submit(worker, func_key, idx)
                future.add_done_callback(update_progress)
                futures.append(future)

            for future in as_completed(futures):
                future.result()

        # 严格类型匹配
        analyze_callsite_type_matching("strict")

        # Cast类型匹配
        analyze_callsite_type_matching("cast")

        # Uncertain类型匹配
        analyze_callsite_type_matching("uncertain")


    def process_callsite_target(self, callsite_text: str,
                                src_func_name: str, src_func_text: str,
                                target_analyze_log_dir: str, func_key: str, idx: int, typ: str) -> bool:
        func_info: FuncInfo = self.collector.func_info_dict[func_key]
        target_func_name: str = func_info.func_name
        target_func_text: str = func_info.func_def_text
        user_prompt = User_Match.format(icall_expr=callsite_text,
                                        src_func_name=src_func_name,
                                        source_function_text=src_func_text,
                                        target_func_name=target_func_name,
                                        target_function_text=target_func_text)
        if not self.double_prompt:
            user_prompt += ("\n\n" + supplement_prompts["user_prompt_match"])

        contents: List[str] = [System_Match, user_prompt]
        return self.query_llm(contents, target_analyze_log_dir, f"{typ}-{idx}.txt")


    def process_macro_callsite_target(self, callsite_text: str, expanded_macro: str, macro_call_expr: str,
                                      src_func_name: str, src_func_text: str,
                                      target_analyze_log_dir: str, func_key: str, idx: int, typ: str) -> bool:
        func_info: FuncInfo = self.collector.func_info_dict[func_key]
        target_func_name: str = func_info.func_name
        target_func_text: str = func_info.func_def_text
        user_prompt = User_Match_macro.format(icall_expr=callsite_text,
                                        src_func_name=src_func_name,
                                        source_function_text=src_func_text,
                                        macro_call_expr=macro_call_expr,
                                        macro_text=expanded_macro,
                                        target_func_name=target_func_name,
                                        target_function_text=target_func_text)
        if not self.double_prompt:
            user_prompt += ("\n\n" + supplement_prompts["user_prompt_match"])

        contents: List[str] = [System_Match, user_prompt]
        return self.query_llm(contents, target_analyze_log_dir, f"{typ}-{idx}.txt")


    def query_llm(self, contents: List[str], target_analyze_log_dir, file_name) -> bool:
        prompt_log: str = ""

        prompt_log += "query:\n{}\n\n{}\n=========================\n".format(contents[0], contents[1])

        yes_time = 0
        # 投票若干次
        for i in range(self.args.vote_time):
            answer: str = self.llm_analyzer.get_response(contents)
            prompt_log += "vote {}:\n{}\n\n".format(i + 1, answer)
            # 如果回答的太长了，让它summarize一下
            tokens = answer.split(' ')
            if len(tokens) >= 8:
                summarizing_template = summarizing_prompt_4_model.\
                    get(self.llm_analyzer.model_type, summarizing_prompt)
                summarizing_text: str = summarizing_template.format(answer)
                answer = self.llm_analyzer.get_response([summarizing_text])
                prompt_log += "***************************\nsummary {}:\n{}\n\n".format(i + 1, answer)

            if 'yes' in answer.lower():
                yes_time += 1
                prompt_log += "Answer: Yes\n\n"
            else:
                prompt_log += "Answer: No\n\n"
            prompt_log += "------------------------------\n\n"

        flag = (yes_time > (self.args.vote_time / 2))
        prompt_log += "Final Answer: {}\n\n".format(flag)
        # 如果需要log
        if self.log_flag:
            prompt_file = file_name
            open(os.path.join(target_analyze_log_dir, prompt_file), 'w', encoding='utf-8') \
                .write(prompt_log)

        return flag