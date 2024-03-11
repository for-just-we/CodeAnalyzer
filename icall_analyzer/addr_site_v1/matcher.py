import time

from icall_analyzer.signature_match.matcher import TypeAnalyzer
from icall_analyzer.llm.base_analyzer import BaseLLMAnalyzer
from icall_analyzer.base_utils.prompts import System_ICall_Summary, \
    User_ICall_Summary_Macro, User_ICall_Summary, System_Func_Summary, User_Func_Summary
from icall_analyzer.llm.common_prompt import summarizing_prompt
from icall_analyzer.base_utils.prompts import supplement_prompts
from icall_analyzer.addr_site_v1.prompts import System_Match, User_Match

from code_analyzer.utils.addr_taken_sites_util import AddrTakenSiteRetriver
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


class AddrSiteMatcherV1:
    def __init__(self, collector: BaseInfoCollector,
                 args,
                 type_analyzer: TypeAnalyzer,
                 addr_taken_site_retriver: AddrTakenSiteRetriver,
                 llm_analyzer: BaseLLMAnalyzer = None,
                 project="",
                 callsite_idxs: Dict[str, int] = None,
                 func_name_2_key: Dict[str, str] = None):
        self.func_key_2_name: Dict[str, str] = func_name_2_key

        self.collector: BaseInfoCollector = collector
        self.args = args
        self.addr_taken_site_retriver: AddrTakenSiteRetriver \
            = addr_taken_site_retriver

        # 保存类型匹配的callsite
        self.type_matched_callsites: Dict[str, Set[str]] = type_analyzer.callees.copy()
        for key, values in type_analyzer.llm_declarator_analysis.items():
            self.type_matched_callsites[key] = self.type_matched_callsites.get(key, set()) | values

        # 保存最终匹配的callsite
        self.matched_callsites: DefaultDict[str, Set[str]] = defaultdict(set)

        self.macro_callsites: Set[str] = type_analyzer.macro_callsites
        self.icall_2_func: Dict[str, str] = type_analyzer.icall_2_func
        self.icall_nodes: Dict[str, ASTNode] = type_analyzer.icall_nodes

        # 每一个indirect-call对应的函数指针声明的文本
        self.icall_2_decl_text: Dict[str, str] = type_analyzer.icall_2_decl_text
        # 每一个indirect-call对应的函数指针声明文本，保留原始类型
        self.icall_2_decl_type_text: Dict[str, str] = type_analyzer.icall_2_decl_type_text
        # 如果icall引用了结构体的field，找到对应的结构体名称
        self.icall_2_struct_name: Dict[str, str] = type_analyzer.icall_2_struct_name

        self.llm_analyzer: BaseLLMAnalyzer = llm_analyzer
        self.callsite_idxs: Dict[str, int] = callsite_idxs

        self.expanded_macros: Dict[str, str] = type_analyzer.expanded_macros
        self.macro_call_exprs: Dict[str, str] = type_analyzer.macro_call_exprs

        # log的位置
        self.log_flag: bool = args.log_llm_output
        if self.log_flag:
            root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
            self.log_dir = f"{root_path}/experimental_logs/addr_site_v1_analysis/" \
                           f"{self.args.running_epoch}/{self.llm_analyzer.model_name}/" \
                           f"{project}"
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir)

    def generate_icall_additional(self, callsite_key, icall_text) -> str:
        if callsite_key in self.icall_2_decl_text.keys():
            decl_text = self.icall_2_decl_text[callsite_key]
            messages = ["The declarator of function pointer in {} is {}.".format(icall_text, decl_text)]
            if callsite_key in self.icall_2_decl_type_text.keys():
                messages.append("The alias type definition of the function type is {}."
                                .format(self.icall_2_decl_type_text[callsite_key]))
            if callsite_key in self.icall_2_struct_name.keys():
                struct_name = self.icall_2_struct_name[callsite_key]
                struct_decl = self.collector.struct_name2declarator[struct_name]
                messages.append("The function pointer of the indirect-call is a field of struct {},"
                                "where its definition is: \n{}.".format(struct_name, struct_decl))
            messages.append("\nThe information below can also help you identify the functionlity of the indirect-call.")

            return "\n".join(messages)

        return ""

    def process_all(self):
        logging.info("Start address-taken site matching...")

        if os.path.exists(f"{self.log_dir}/semantic_result.txt"):
            logging.info("loading existed semantic matching results automatically")
            with open(f"{self.log_dir}/semantic_result.txt", "r", encoding='utf-8') as f:
                for line in f:
                    tokens: List[str] = line.strip().split('|')
                    callsite_key: str = tokens[0]
                    func_keys: Set[str] = set()
                    if len(tokens) > 1:
                        func_keys.update(tokens[1].split(','))
                    self.matched_callsites[callsite_key] = func_keys
                    self.type_matched_callsites.pop(callsite_key)

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
                    func_keys = set(filter(lambda func_key:
                                           self.func_key_2_name.get(func_key, '') in self.collector.refered_funcs,
                                           func_keys))
                    self.matched_callsites[callsite_key] = func_keys
                    self.type_matched_callsites.pop(callsite_key)

            return


        logging.info("{} callsite to be analyzed".format(len(self.type_matched_callsites)))
        time.sleep(2)

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
            callsite_node: ASTNode = self.icall_nodes[callsite_key]
            callsite_text: str = callsite_node.node_text

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
        icall_additional = self.generate_icall_additional(callsite_key, callsite_text)

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
            flag = self.process_callsite_target(callsite_text, icall_additional,
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


    def process_callsite_target(self, callsite_text: str, icall_additional: str,
                                icall_summary: str, target_analyze_log_dir: str, func_key: str, idx: int) -> bool:

        func_info: FuncInfo = self.collector.func_info_dict[func_key]
        func_name: str = func_info.func_name
        func_def_text: str = func_info.func_def_text
        prompt_log: str = ""

        system_prompt_func: str = System_Func_Summary.format(func_name=func_name)
        user_prompt_func: str = User_Func_Summary.format(func_name=func_name,
                                                         func_body=func_def_text)
        prompt_log += "{}\n\n{}\n\n======================\n".format(system_prompt_func, user_prompt_func)

        # 生成target function summary
        func_summary: str = self.llm_analyzer.get_response([system_prompt_func,
                                                            user_prompt_func])
        prompt_log += "{}:\n{}\n=========================\n".format(self.llm_analyzer.model_name,
                                                                    func_summary)

        # 生成target function的address_taken_information
        target_additional_information = self.addr_taken_site_retriver.\
            random_select_one(func_name)

        # 进行匹配
        add_suffix = False
        user_prompt_match: str = User_Match.format(icall_expr=callsite_text,
                                                   icall_additional=icall_additional,
                                                   icall_summary=icall_summary,
                                                   func_summary=func_summary,
                                                   func_name=func_name,
                                                   target_additional_information=target_additional_information)
        # 如果不需要二段式，也就是不需要COT
        user_prompt_match += ("\n\n" + supplement_prompts["user_prompt_match"])


        return self.query_llm([System_Match, user_prompt_match], target_analyze_log_dir, f"{idx}.txt", add_suffix, prompt_log)

    def query_llm(self, contents: List[str], target_analyze_log_dir, file_name, add_suffix, prompt_log: str) -> bool:
        prompt_log += "query:\n{}\n\n{}\n=========================\n".format(contents[0], contents[1])

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