from icall_analyzer.signature_match.matcher import TypeAnalyzer
from icall_analyzer.llm.base_analyzer import BaseLLMAnalyzer
from icall_analyzer.base_utils.prompts import System_ICall_Summary, \
    User_ICall_Summary_Macro, User_ICall_Summary
from icall_analyzer.llm.common_prompt import summarizing_prompt
from icall_analyzer.multi_step_match.prompt import User_Match, System_Match, supplement_prompts

from code_analyzer.definition_collector import BaseInfoCollector
from code_analyzer.schemas.ast_node import ASTNode
from code_analyzer.schemas.function_info import FuncInfo

from tqdm import tqdm
import os
import logging
from typing import Dict, Set, DefaultDict, List
from collections import defaultdict

from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


class MultiStepMatcher:
    def __init__(self, collector: BaseInfoCollector,
                 args,
                 type_analyzer: TypeAnalyzer,
                 func_key2summary: Dict[str, str],
                 llm_analyzer: BaseLLMAnalyzer = None,
                 project="",
                 callsite_idxs: Dict[str, int] = None):
        self.collector: BaseInfoCollector = collector
        self.args = args
        # func key映射为summary
        self.func_key2summary: Dict[str, str] = func_key2summary

        # 保存类型匹配的callsite
        self.type_matched_callsites: Dict[str, Set[str]] = type_analyzer.callees.copy()
        for key, values in type_analyzer.llm_declarator_analysis.items():
            self.type_matched_callsites[key] = self.type_matched_callsites.get(key, set()) | values

        # 保存最终匹配的callsite
        self.matched_callsites: DefaultDict[str, Set[str]] = defaultdict(set)

        self.macro_callsites: Set[str] = type_analyzer.macro_callsites
        self.icall_2_func: Dict[str, str] = type_analyzer.icall_2_func
        self.icall_nodes: Dict[str, ASTNode] = type_analyzer.icall_nodes

        self.llm_analyzer: BaseLLMAnalyzer = llm_analyzer
        self.callsite_idxs: Dict[str, int] = callsite_idxs

        self.expanded_macros: Dict[str, str] = type_analyzer.expanded_macros
        self.macro_call_exprs: Dict[str, str] = type_analyzer.macro_call_exprs

        # log的位置
        self.log_flag: bool = args.log_llm_output
        if self.log_flag:
            root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
            self.log_dir = f"{root_path}/experimental_logs/multi_step_analysis/" \
                           f"{self.args.running_epoch}/{self.llm_analyzer.model_name}/" \
                           f"{project}"
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir)


    def process_all(self):
        logging.info("Start mutil-step matching...")
        if self.args.load_pre_semantic_analysis_res:
            assert os.path.exists(f"{self.log_dir}/semantic_result.txt")
            logging.info("loading existed semantic matching results.")
            with open(f"{self.log_dir}/semantic_result.txt", "r", encoding='utf-8') as f:
                for line in f:
                    tokens: List[str] = line.strip().split('|')
                    callsite_key: str = tokens[0]
                    func_keys: Set[str] = set()
                    if len(tokens) > 1:
                        func_keys.update(tokens[1].split(','))
                    self.matched_callsites[callsite_key] = func_keys
            return

        # 遍历callsite
        for (callsite_key, func_keys) in self.type_matched_callsites.items():
            if callsite_key not in self.icall_2_func.keys():
                continue
            if callsite_key in self.macro_callsites and self.args.disable_analysis_for_macro:
                continue
            elif callsite_key not in self.macro_callsites and self.args.disable_analysis_for_normal:
                continue

            i = self.callsite_idxs[callsite_key]

            parent_func_key: str = self.icall_2_func[callsite_key]
            parent_func_info: FuncInfo = self.collector.func_info_dict[parent_func_key]
            parent_func_name: str = parent_func_info.func_name
            parent_func_text: str = parent_func_info.func_def_text
            callsite_text: str = self.icall_nodes[callsite_key].node_text

            # 首先找出该callsite所在function
            if callsite_key in self.macro_callsites:
                expanded_macro: str = self.expanded_macros[callsite_key]
                macro_call_expr: str = self.macro_call_exprs[callsite_key]
                user_prompt: str = User_ICall_Summary_Macro.format(icall_expr=callsite_text,
                                                                   macro_call_expr=macro_call_expr,
                                                                   expanded_macro=expanded_macro,
                                                                   func_name=parent_func_name,
                                                                   func_body=parent_func_text)
            else:
                user_prompt: str = User_ICall_Summary.format(icall_expr=callsite_text,
                                                             func_name=parent_func_name,
                                                             func_body=parent_func_text)

            self.process_callsite(callsite_key, i, func_keys, user_prompt, callsite_text)

            # 如果log，记录下分析结果
            if self.log_flag:
                func_keys: Set[str] = self.matched_callsites[callsite_key]
                content: str = callsite_key + "|" + ",".join(func_keys) + "\n"
                with open(f"{self.log_dir}/semantic_result.txt", "a", encoding='utf-8') as f:
                    f.write(content)


    def process_callsite(self, callsite_key: str, i: int, func_keys: Set[str],
                         user_prompt: str, callsite_text: str):
        icall_summary: str = self.llm_analyzer.get_response([System_ICall_Summary, user_prompt])

        cur_log_dir = f"{self.log_dir}/callsite-{i}"
        target_analyze_log_dir = f"{cur_log_dir}/semantic"

        # 如果需要log
        if self.log_flag:
            if not os.path.exists(target_analyze_log_dir):
                os.makedirs(target_analyze_log_dir)
            log_content = "callsite_key: {} \n\n====================\n\n" \
                          "{}\n\n{}\n\n===================\n\n" \
                          "{}".format(callsite_key, System_ICall_Summary,
                                      user_prompt, icall_summary)
            with open(f"{cur_log_dir}/callsite_summary.txt", "w", encoding='utf-8') as f:
                f.write(log_content)

        lock = threading.Lock()
        executor = ThreadPoolExecutor(max_workers=self.args.num_worker)
        pbar = tqdm(total=len(func_keys),
                        desc="semantic matching for callsite-{}: {}"
                        .format(i, callsite_key))
        futures = []

        def update_progress(future):
            pbar.update(1)

        def worker(func_key: str, idx: int):
            flag = self.process_callsite_target(callsite_text,
                                                icall_summary, target_analyze_log_dir, func_key, idx)
            if flag:
                with lock:
                    self.matched_callsites[callsite_key].add(func_key)

        for idx, func_key in enumerate(func_keys):
            future = executor.submit(worker, func_key, idx)
            future.add_done_callback(update_progress)
            futures.append(future)

        for future in as_completed(futures):
            future.result()


    def process_callsite_target(self, callsite_text: str,
                                icall_summary: str, target_analyze_log_dir: str, func_key: str, idx: int) -> bool:
        func_summary: str = self.func_key2summary[func_key]
        func_info = self.collector.func_info_dict[func_key]
        add_suffix = False
        func_name: str = func_info.func_name
        user_prompt_match: str = User_Match.format(icall_expr=callsite_text,
                                                   icall_summary=icall_summary, func_summary=func_summary,
                                                   func_name=func_name)
        user_prompt_match += ("\n\n" + supplement_prompts["user_prompt_match"])

        return self.query_llm([System_Match, user_prompt_match], target_analyze_log_dir,
                              f"{idx}.txt", add_suffix)


    def query_llm(self, contents: List[str], target_analyze_log_dir, file_name, add_suffix) -> bool:
        prompt_log: str = "query:\n{}\n\n{}\n=========================\n".format(contents[0], contents[1])

        yes_time = 0
        # 投票若干次
        for i in range(self.args.vote_time):
            answer: str = self.llm_analyzer.get_response(contents, add_suffix)
            prompt_log += "vote {}:\n{}\n\n".format(i + 1, answer)
            # 如果回答的太长了，让它summarize一下
            tokens = answer.split(' ')
            if len(tokens) >= 8:
                summarizing_text: str = summarizing_prompt.format(answer)
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