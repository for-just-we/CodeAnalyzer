from code_analyzer.definition_collector import BaseInfoCollector
from code_analyzer.schemas.ast_node import ASTNode
from code_analyzer.schemas.function_info import FuncInfo

from icall_analyzer.llm.common_prompt import summarizing_prompt
from icall_analyzer.llm.base_analyzer import BaseLLMAnalyzer
from icall_analyzer.signature_match.matcher import TypeAnalyzer
from icall_analyzer.single_step_complex_match.prompt import System_Match, User_Match, \
    FuncPointerDeclaratorPrompt, TypeMessagePrompt1, TypeMessagePrompt2, TypeMessagePrompt3, \
    supplement_prompts

from tqdm import tqdm
import os
import logging
from typing import Dict, Set, DefaultDict, List
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import threading

idx_text_gen = {1: '2nd', 2: '3rd'}
idx_2_text = lambda idx: idx_text_gen.get(idx, f'{idx + 1}th')

class SingleStepComplexMatcher:
    def __init__(self, collector: BaseInfoCollector,
                 args,
                 type_analyzer: TypeAnalyzer,
                 llm_analyzer: BaseLLMAnalyzer = None,
                 callsite_keys: Set[str] = None,
                 project=""):
        self.collector: BaseInfoCollector = collector
        # 是否采用二段式prompt
        self.double_prompt: bool = args.double_prompt
        self.args = args
        self.callsite_keys: Set[str] = callsite_keys

        self.icall_2_decl_text: Dict[str, str] = type_analyzer.icall_2_decl_text
        self.icall_2_decl_var_text: Dict[str, str] = type_analyzer.icall_2_decl_var_text
        self.icall_2_arg_declarators: Dict[str, List[List[str]]] = type_analyzer.icall_2_arg_declarators
        self.icall_2_arg_texts: Dict[str, List[str]] = type_analyzer.icall_2_arg_texts
        self.icall_2_arg_text: Dict[str, str] = type_analyzer.icall_2_arg_text

        self.uncertain_idxs: DefaultDict[str, Dict[str, Set[int]]] = type_analyzer.uncertain_idxs

        self.icall_2_func: Dict[str, str] = type_analyzer.icall_2_func
        self.icall_nodes: Dict[str, ASTNode] = type_analyzer.icall_nodes
        self.macro_callsites: Set[str] = type_analyzer.macro_callsites

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

        # log的位置
        self.log_flag: bool = args.log_llm_output
        if self.log_flag:
            root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
            epoch_sig: str = str(self.args.running_epoch)
            if self.args.double_prompt:
                epoch_sig += "-double"
            self.log_dir = f"{root_path}/experimental_logs/single_step_complex_analysis/{epoch_sig}/{self.llm_analyzer.model_name}/" \
                           f"{project}"
            self.res_log_file = f"{self.log_dir}/single_step_complex_result.txt"
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir)

    def process_all(self):
        logging.info("Start single step complex matching...")

        if self.args.load_pre_single_step_analysis_res:
            assert os.path.exists(self.res_log_file)
            logging.info("loading existed single step complex matching results.")
            with open(self.res_log_file, "r", encoding='utf-8') as f:
                for line in f:
                    tokens: List[str] = line.strip().split('|')
                    callsite_key: str = tokens[0]
                    func_keys: Set[str] = set()
                    if len(tokens) > 1:
                        func_keys.update(tokens[1].split(','))
                    self.matched_callsites[callsite_key] = func_keys
            return

        for i, callsite_key in enumerate(self.callsite_keys):
            if callsite_key not in self.icall_2_func.keys():
                continue

            # 首先找出该callsite所在function
            parent_func_key: str = self.icall_2_func[callsite_key]
            parent_func_info: FuncInfo = self.collector.func_info_dict[parent_func_key]
            src_func_name: str = parent_func_info.func_name
            src_func_text: str = parent_func_info.func_def_text
            callsite_text: str = self.icall_nodes[callsite_key].node_text
            func_pointer_text: str = self.icall_2_decl_text.get(callsite_key, "")
            func_pointer_var_text: str = self.icall_2_decl_var_text.get(callsite_key, "")

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
                executor = ThreadPoolExecutor(max_workers=self.args.num_workers)
                pbar = tqdm(total=len(matched_func_keys),
                            desc=f"semantic matching for {match_type} type matched callsite-{i}: {callsite_key}")
                futures = []

                def update_progress(future):
                    pbar.update(1)

                def worker(func_key: str, idx: int):
                    flag = self.process_callsite_target(callsite_text, callsite_key, src_func_name, src_func_text,
                                                        target_analyze_log_dir, func_key, idx, match_type,
                                                        func_pointer_text, func_pointer_var_text)
                    if flag:
                        with lock:
                            self.matched_callsites[callsite_key].add(func_key)

                for idx, func_key in enumerate(matched_func_keys):
                    future = executor.submit(worker, func_key, idx)
                    future.add_done_callback(update_progress)
                    futures.append(future)


            # 严格类型匹配
            analyze_callsite_type_matching("strict")
            # Cast类型匹配
            analyze_callsite_type_matching("cast")
            # uncertain类型匹配
            analyze_callsite_type_matching("uncertain")

            # 如果log，记录下分析结果
            if self.log_flag:
                func_keys: Set[str] = self.matched_callsites[callsite_key]
                content: str = callsite_key + "|" + ",".join(func_keys) + "\n"
                with open(self.res_log_file, "a", encoding='utf-8') as f:
                    f.write(content)

    def process_callsite_target(self, callsite_text: str, callsite_key: str,
                                src_func_name: str, src_func_text: str,
                                target_analyze_log_dir: str, func_key: str,
                                idx: int, typ: str,
                                func_pointer_text: str,
                                func_pointer_var_text: str) -> bool:
        func_info: FuncInfo = self.collector.func_info_dict[func_key]
        target_func_name: str = func_info.func_name
        target_func_text: str = func_info.func_def_text

        additional_info_icall = func_pointer_text
        if func_pointer_var_text != "":
            additional_info_icall += ("\n" + func_pointer_var_text)

        if additional_info_icall != "":
            additional_info_icall = FuncPointerDeclaratorPrompt.format(additional_info_icall)

        type_message = TypeMessagePrompt3
        # 需要类型匹配
        if typ == "uncertain":
            # 如果找到了函数指针定义
            if func_pointer_text != "":
                type_message = TypeMessagePrompt1.format(func_pointer=func_pointer_text,
                                                         func_declarator=target_func_text)
            else:
                uncertain_idxs: Set[int] = self.uncertain_idxs[callsite_key][func_key]
                sorted_list: List[int] = sorted(uncertain_idxs)
                idx_text: str = ','.join(idx_2_text(idx) for idx in sorted_list)
                param_decl_texts: List[str] = self.collector.func_info_dict[func_key].declarator_texts

                arg_texts: List[str] = self.icall_2_arg_texts.get(callsite_key, None)
                arg_list_text: str = self.icall_2_arg_text.get(callsite_key, "")
                decl_contexts: List[List[str]] = self.icall_2_arg_declarators.get(callsite_key, None)

                items: List[str] = list()

                if decl_contexts is not None and arg_texts is not None and param_decl_texts is not None:
                    for idx in sorted_list:
                        temp_text: str = ""
                        if idx < len(arg_texts):
                            temp_text += "The expression of {} argument is: {}\n"\
                                .format(idx_2_text(idx), arg_texts[idx])
                        if idx < len(param_decl_texts):
                            temp_text += "The declaration of {} function parameter is: {}\n".format(idx_2_text(idx),
                                                                                                param_decl_texts[idx])
                        if len(decl_contexts[idx]) != 0:
                            temp_text += "The declarations of variables in {} argument are:\n{}".format(idx_2_text(idx),
                                                                                                    '\n'.join(
                                                                                                        decl_contexts[
                                                                                                     idx]))
                        items.append(temp_text)

                decl_context_text: str = "\n\n".join(items)
                type_message = TypeMessagePrompt2.format(idx=idx_text, arg_text=arg_list_text,
                                                         func_decl_text=self.collector.func_key_2_declarator[func_key],
                                                         contexts=decl_context_text)

        total_user_prompt = User_Match.format(icall_expr=callsite_text,
                                              src_func_name=src_func_name,
                                              source_function_text=src_func_text,
                                              target_func_name=target_func_name,
                                              target_function_text=target_func_text,
                                              additional_info=additional_info_icall,
                                              type_messge=type_message)

        if not self.double_prompt:
            total_user_prompt += ("\n\n" + supplement_prompts["user_prompt_match"])

        contents: List[str] = [System_Match, total_user_prompt]
        prompt_log: str = ""
        prompt_log += "query:\n{}\n\n{}\n=========================\n".format(System_Match,
                                                                             total_user_prompt)
        yes_time = 0

        # 投票若干次
        for i in range(self.args.vote_time):
            answer: str = self.llm_analyzer.get_response(contents)
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
            prompt_file = f"{typ}-{idx}.txt"
            open(os.path.join(target_analyze_log_dir, prompt_file), 'w', encoding='utf-8') \
                .write(prompt_log)

        return flag