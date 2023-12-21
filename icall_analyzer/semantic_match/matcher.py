from code_analyzer.definition_collector import BaseInfoCollector
from code_analyzer.schemas.ast_node import ASTNode
from code_analyzer.schemas.function_info import FuncInfo

from icall_analyzer.llm.common_prompt import summarizing_prompt
from icall_analyzer.llm.base_analyzer import BaseLLMAnalyzer
from icall_analyzer.signature_match.matcher import TypeAnalyzer
from icall_analyzer.semantic_match.base_prompt import System_ICall_Summary, User_ICall_Summary, \
                                System_Func_Summary, User_Func_Summary, \
                                System_Match, User_Match, supplement_prompts

from tqdm import tqdm
import os
import logging
from typing import Dict, Set, DefaultDict, List
from collections import defaultdict

class SemanticMatcher:
    def __init__(self, collector: BaseInfoCollector,
                 args,
                 type_analyzer: TypeAnalyzer,
                 llm_analyzer: BaseLLMAnalyzer = None,
                 project=""):
        self.collector: BaseInfoCollector = collector
        # 是否采用二段式prompt
        self.double_prompt: bool = args.double_prompt
        self.args = args
        # 保存类型匹配的callsite
        self.type_matched_callsites: Dict[str, Set[str]] = type_analyzer.callees
        for key, values in type_analyzer.llm_declarator_analysis.items():
            self.type_matched_callsites[key] = self.type_matched_callsites.get(key, set()) | values

        # 保存语义匹配的callsite
        self.matched_callsites: DefaultDict[str, Set[str]] = defaultdict(set)

        self.icall_2_func: Dict[str, str] = type_analyzer.icall_2_func
        self.icall_nodes: Dict[str, ASTNode] = type_analyzer.icall_nodes

        self.llm_analyzer: BaseLLMAnalyzer = llm_analyzer

        # log的位置
        self.log_flag: bool = args.log_llm_output
        if self.log_flag:
            root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
            self.log_dir = f"{root_path}/experimental_logs/semantic_analysis/{self.args.running_epoch}/{self.llm_analyzer.model_name}/" \
                      f"{project}"
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir)

    def process_all(self):
        logging.info("Start semantic matching...")
        # 遍历callsite
        for i, (callsite_key, func_keys) in enumerate(self.type_matched_callsites.items()):
            # 首先找出该callsite所在function
            parent_func_key: str = self.icall_2_func[callsite_key]
            parent_func_info: FuncInfo = self.collector.func_info_dict[parent_func_key]
            parent_func_name: str = parent_func_info.func_name
            parent_func_text: str = parent_func_info.func_def_text
            callsite_text: str = self.icall_nodes[callsite_key].node_text

            user_prompt: str = User_ICall_Summary.format(icall_expr=callsite_text,
                                                         func_name=parent_func_name,
                                                         func_body=parent_func_text)
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

            for idx, func_key in tqdm(enumerate(func_keys), desc="semantic matching for callsite-{}: {}"
                    .format(i, callsite_key)):
                flag = self.process_callsite_target(callsite_text,
                                             icall_summary, target_analyze_log_dir, func_key, idx)
                if flag:
                    self.matched_callsites[callsite_key].add(func_key)

            # 如果log，记录下分析结果
            if self.log_flag:
                func_keys: Set[str] = self.matched_callsites[callsite_key]
                content: str = callsite_key + "|" + ",".join(func_keys) + "\n"
                with open(f"{self.log_dir}/semantic_result.txt", "a", encoding='utf-8') as f:
                    f.write(content)

    def process_callsite_target(self, callsite_text: str,
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
        prompt_log += "{}:\n{}\n=========================\n".format(self.llm_analyzer.model_name, func_summary)

        # 进行匹配
        user_prompt_match: str = User_Match.format(icall_expr=callsite_text,
            icall_summary=icall_summary, func_summary=func_summary, func_name=func_name)
        if not self.double_prompt:
            user_prompt_match += ("\n\n" + supplement_prompts["user_prompt_match"])

        contents: List[str] = [System_Match, user_prompt_match]

        prompt_log += "query:\n{}\n\n{}\n=========================\n".format(System_Match, user_prompt_match)

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
            prompt_file = f"{idx}.txt"
            open(os.path.join(target_analyze_log_dir, prompt_file), 'w', encoding='utf-8') \
                .write(prompt_log)

        return flag