from typing import Set, Dict
from code_analyzer.schemas.function_info import FuncInfo

from icall_analyzer.llm.base_analyzer import BaseLLMAnalyzer
from icall_analyzer.base_utils.prompts import System_Func_Summary, User_Func_Summary

from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import threading
from tqdm import tqdm
import logging

class FunctionSummarizer:
    def __init__(self, func_keys: Set[str],
                 func_info_dict: Dict[str, FuncInfo],
                 args,
                 llm_analyzer: BaseLLMAnalyzer = None):
        self.func_keys: Set[str] = func_keys
        self.func_info_dict: Dict[str, FuncInfo] = func_info_dict
        # 将func_key映射为func_summary
        self.func_key2summary: Dict[str, str] = dict()
        self.llm_analyzer: BaseLLMAnalyzer = llm_analyzer
        self.args = args

    def analyze(self):
        lock = threading.Lock()

        def analyze_func(func_key: str):
            func_info: FuncInfo = self.func_info_dict[func_key]
            func_name: str = func_info.func_name
            func_def_text: str = func_info.func_def_text

            system_prompt_func: str = System_Func_Summary.format(func_name=func_name)
            user_prompt_func: str = User_Func_Summary.format(func_name=func_name,
                                                             func_body=func_def_text)

            func_summary: str = self.llm_analyzer.get_response([system_prompt_func,
                                                                user_prompt_func])

            with lock:
                self.func_key2summary[func_key] = func_summary

        def update_progress(future):
            pbar.update(1)

        executor = ThreadPoolExecutor(max_workers=self.args.num_worker)
        pbar = tqdm(total=len(self.func_keys), desc="summarizing address-taken function")
        futures = []

        for func_key in self.func_keys:
            future = executor.submit(analyze_func, func_key)
            future.add_done_callback(update_progress)
            futures.append(future)

        for future in as_completed(futures):
            future.result()

        logging.info("summarizied {} functions, should summarize {} functions"
                     .format(len(self.func_key2summary), len(self.func_keys)))
        assert len(self.func_key2summary) == len(self.func_keys)