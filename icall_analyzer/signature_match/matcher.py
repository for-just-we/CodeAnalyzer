from code_analyzer.definition_collector import BaseInfoCollector
from code_analyzer.visit_utils.base_util import loc_inside
from code_analyzer.visit_utils.type_util import parsing_type, get_original_type
from code_analyzer.schemas.function_info import FuncInfo
from code_analyzer.visitors.func_visitor import FunctionBodyVisitor
from icall_analyzer.llm.base_analyzer import BaseLLMAnalyzer
from icall_analyzer.signature_match.prompt import system_prompt, user_prompt, \
    system_prompt_declarator, user_prompt_declarator, summarizing_prompt

from scope_strategy.base_strategy import BaseStrategy
from code_analyzer.schemas.ast_node import ASTNode

import os
from tqdm import tqdm
from collections import defaultdict
from typing import Dict, List, Tuple, Set, DefaultDict
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import threading

class TypeAnalyzer:
    def __init__(self, collector: BaseInfoCollector,
                 args,
                 scope_strategy: BaseStrategy = None,
                 llm_analyzer: BaseLLMAnalyzer = None,
                 project: str = ""):
        self.collector: BaseInfoCollector = collector
        # 保存每个indirect-callsite的代码文本
        self.icall_nodes: Dict[str, ASTNode] = dict()
        # 保存每个indirect-callsite所在的function
        self.icall_2_func: Dict[str, str] = dict()
        # scope策略
        self.scope_strategy: BaseStrategy = scope_strategy

        # 保存匹配上的函数名
        self.callees: Dict[str, Set[str]] = dict()
        # 将宏函数间接调用点映射为宏名称
        self.macro_icall2_callexpr: Dict[str, str] = dict()
        # 保存每个indirect-callsite的代码文本
        self.icall_nodes: Dict[str, ASTNode] = dict()
        # 保存每个indirect-callsite所在的function
        self.icall_2_func: Dict[str, str] = dict()

        self.llm_analyzer: BaseLLMAnalyzer = llm_analyzer
        # 如果LLM已经分析了两个结构体类型，跳过
        self.llm_analyzed_types: Dict[Tuple[str, str], bool] = dict()
        # 线程数
        self.num_worker: int = args.num_worker
        logging.info("thread num: {}".format(self.num_worker))

        self.log_flag: bool = args.log_llm_output
        self.load_pre_type_analysis_res: bool = args.load_pre_type_analysis_res
        self.running_epoch: int = args.running_epoch
        self.macro_callsites: Set[str] = set()

        self.vote_time: int = args.vote_time

        # 如果需要log LLM的输出结果或者加载LLM预先分析的结果
        if self.log_flag or self.load_pre_type_analysis_res:
            # llm帮助分析过的icall以及func_key
            self.llm_helped_type_analysis_icall_pair: DefaultDict[str, Set[str]] = defaultdict(set)
            self.llm_declarator_analysis: DefaultDict[str, Set[str]] = defaultdict(set)
            root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
            log_dir = f"{root_path}/experimental_logs/type_analysis/{self.running_epoch}/{self.llm_analyzer.model_name}/" \
                      f"{project}"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            self.log_type_alias_file = f"{log_dir}/type_alias_info.txt"
            self.log_declarator_res = os.path.join(log_dir, "llm_declarator_analysis.txt")
            self.log_dir = log_dir
            self.struct_analysis_log_path = os.path.join(log_dir, "struct_relation")
            self.declarator_analysis_log_path = os.path.join(log_dir, "declarator_relation")

            # 需要log的话先设置好log路径，并清空相应文件
            if self.log_flag and llm_analyzer is not None:
                if not os.path.exists(self.struct_analysis_log_path):
                    os.mkdir(self.struct_analysis_log_path)
                if not os.path.exists(self.declarator_analysis_log_path):
                    os.mkdir(self.declarator_analysis_log_path)

                # 清空内容
                with open(self.log_declarator_res, 'w', encoding='utf-8'):
                    pass

            # 需要加载之前log分析结果
            if self.load_pre_type_analysis_res:
                # 如果llm之前已经分析过类型，那么导入已有的类型信息
                if os.path.exists(self.log_type_alias_file):
                    with open(self.log_type_alias_file, 'r', encoding='utf-8') as file:
                        lines = file.readlines()
                        for line in lines:
                            if line == "\n":
                                continue
                            struct_names, flag = line.strip().split(':')
                            struct_name_set = struct_names.split(',')
                            struct_name1, struct_name2 = struct_name_set[0], struct_name_set[1]
                            self.llm_analyzed_types[(struct_name1, struct_name2)] = bool(flag)
                        logging.info("loading analyzed type infos, size is: {}".format(len(self.llm_analyzed_types)))

                # 如果llm已经分析过declarator，导入过已有的declarator分析信息
                if os.path.exists(self.log_declarator_res):
                    with open(self.log_declarator_res, 'r', encoding='utf-8') as file:
                        lines = file.readlines()
                        for line in lines:
                            if line == "\n":
                                continue
                            callsite_key, func_keys_str = line.strip().split('|')
                            func_keys: Set[str] = func_keys_str.split(',')
                            self.llm_declarator_analysis[callsite_key].update(func_keys)
                        logging.info("loading analyzed declarators, size is: {}"
                                .format(len(self.llm_declarator_analysis)))


        self.processed_icall_num: int = 1

    def process_all(self):
        # 遍历每个函数
        for func_key, func_info in self.collector.func_info_dict.items():
            icall_locs: List[Tuple[int, int]] = self.collector.icall_dict.get(
                func_info.file, list())
            start_point: Tuple[int, int] = func_info.func_body.start_point
            end_point: Tuple[int, int] = func_info.func_body.end_point
            icall_locs_in_cur_func: List[Tuple[int, int]] = list(filter(
                lambda icall_loc: loc_inside(icall_loc, start_point, end_point),
                icall_locs
            ))

            # 当前函数中存在indirect-callsite
            if len(icall_locs_in_cur_func) > 0:
                self.process_function(func_key, func_info, icall_locs_in_cur_func)

    # 处理一个函数中的indirect-call
    def process_function(self, func_key: str, func_info: FuncInfo, icall_locs: List[Tuple[int, int]]):
        arg_info: Dict[str, str] = {parameter_type[1]: parameter_type[0]
                                       for parameter_type in func_info.parameter_types}
        func_body_visitor: FunctionBodyVisitor = FunctionBodyVisitor(
            icall_locs, arg_info, func_info.name_2_declarator_text, func_info.local_var,
        func_info.local_var2declarator, self.collector)
        # 设置局部变量和形参涉及到函数指针的信息
        if hasattr(func_info, "func_var2param_types"):
            func_body_visitor.set_func_var2param_types(func_info.func_var2param_types)
        if hasattr(func_info, "func_param2param_types"):
            func_body_visitor.set_func_param2param_types(func_info.func_param2param_types)
        if hasattr(func_info, "var_arg_func_param"):
            func_body_visitor.set_var_arg_func_param(func_info.var_arg_func_param)
        if hasattr(func_info, "var_arg_func_var"):
            func_body_visitor.set_var_arg_func_var(func_info.var_arg_func_var)

        func_body_visitor.traverse_node(func_info.func_body)
        # 遍历当前function中的每一个indirect-call
        for icall_loc in icall_locs:
            callsite_key: str = f"{func_info.file}:{icall_loc[0] + 1}:{icall_loc[1] + 1}"
            # 如果该indirect-call对应的call expression没有被正确解析，跳过。
            logging.info("visiting {}-th icall {}".format(self.processed_icall_num, callsite_key))
            if icall_loc not in func_body_visitor.icall_nodes.keys():
                self.callees[callsite_key] = set()
                continue
            self.icall_nodes[callsite_key] = func_body_visitor.icall_nodes[icall_loc]
            self.icall_2_func[callsite_key] = func_key
            self.process_indirect_call(callsite_key, icall_loc, func_body_visitor)
            self.processed_icall_num += 1



    # 处理一个indirect-call
    def process_indirect_call(self, callsite_key: str, icall_loc: Tuple[int, int],
                              func_body_visitor: FunctionBodyVisitor):
        # 如果不是宏函数
        if icall_loc not in func_body_visitor.current_macro_funcs.keys():
            # 根据参数的类型进行间接调用匹配
            arg_type: List[Tuple[str, int]] = \
                func_body_visitor.arg_info_4_callsite.get(icall_loc)
            if arg_type is not None:
                self.match_with_types(arg_type, callsite_key)
            else:
                logging.debug("error parsing arguments for {}-th indirect-callsite: {}".
                              format(self.processed_icall_num, callsite_key))

            # 根据函数指针声明的形参类型进行匹配
            func_pointer_arg_type: List[str] = func_body_visitor.icall_2_decl_param_types.\
                get(icall_loc, None)
            if func_pointer_arg_type is not None:
                func_pointer_arg_types: List[Tuple[str, int]] = [
                    (t, 0) for t in func_pointer_arg_type
                ]
                var_arg: bool = (icall_loc in func_body_visitor.var_arg_icalls)
                arg_num = len(func_pointer_arg_type)
                self.match_with_types(func_pointer_arg_types, callsite_key, var_arg)
            else:
                logging.debug("fail to find function pointer declaration for {}-th indirect-callsite: {}".
                              format(self.processed_icall_num, callsite_key))
                arg_num = 0
                var_arg = False

            # 根据函数指针declarator和function declarator进行匹配
            function_pointer_declarator: str = func_body_visitor\
                .icall_2_decl_text.get(icall_loc, None)
            # 需要llm辅助类型分析
            if self.llm_analyzer is not None and \
                    function_pointer_declarator is not None:
                logging.info("function pointer declarator is: {}".format(function_pointer_declarator))
                self.match_with_declarator_texts(function_pointer_declarator, callsite_key,
                                                arg_num, var_arg)

            # 有llm帮忙分析的callsite_key
            # 把llm的中间结果log出来
            if self.log_flag:
                if hasattr(self, "llm_helped_type_analysis_icall_pair") \
                    and len(self.llm_helped_type_analysis_icall_pair[callsite_key]) > 0:
                    content: str = \
                        f"{callsite_key}|{','.join(self.llm_helped_type_analysis_icall_pair[callsite_key])}"
                    dump_file = os.path.join(self.log_dir, "llm_helped_type_analysis.txt")
                    open(dump_file, 'a', encoding='utf-8').write(content + "\n")

                if hasattr(self, "llm_declarator_analysis") \
                    and len(self.llm_declarator_analysis[callsite_key]) > 0:
                    content: str = \
                        f"{callsite_key}|{','.join(self.llm_declarator_analysis[callsite_key])}"
                    open(self.log_declarator_res, 'a', encoding='utf-8').write(content + "\n")

        else:
            self.macro_callsites.add(callsite_key)

    # 根据参数类型进行匹配
    # 后面两个参数表示原始类型参数名，没有映射到别名类型前的参数名
    def match_types_callsite_target(self, arg_types: List[Tuple[str, int]],
                                    param_types: List[Tuple[str, int]],
                                    ori_arg_type_names: List[str],
                                    ori_param_type_names: List[str]) -> Tuple[bool, bool]:
        """
        :return: 第一个bool表示类型是否匹配，第二个bool表示是否llm帮忙了
        """
        assert len(arg_types) == len(param_types)
        llm_helped_ = False
        # 逐个参数匹配
        for i in range(len(arg_types)):
            arg_type: Tuple[str, int] = arg_types[i]
            param_type: Tuple[str, int] = param_types[i]
            ori_arg_type_name: str = ori_arg_type_names[i]
            ori_param_type_name: str = ori_param_type_names[i]
            flag, llm_helped = self.match_type(arg_type, param_type, ori_arg_type_name, ori_param_type_name)
            llm_helped_ |= llm_helped
            if not flag:
                return False, llm_helped_

        return True, llm_helped_

    def match_type(self, arg_type: Tuple[str, int], param_type: Tuple[str, int],
                   ori_arg_type_name: str, ori_param_type_name: str) -> Tuple[bool, bool]:
        """
        :return: 第一个bool表示类型是否匹配，第二个bool表示是否用到llm作类型判断
        """
        # 如果严格类型匹配成功
        if arg_type[0] == param_type[0] and arg_type[1] == param_type[1]:
            return True, False
        # 考虑结构体、联合体之间的的指针类型转换关系
        # 如果都不是指针类型，不予考虑
        if arg_type[1] == 0 and param_type[1] == 0:
            return False, False
        if self.is_type_contain(arg_type, param_type):
            return True, False
        elif self.is_type_contain(param_type, arg_type):
            return True, False
        # 如果不需要LLM来辅助
        if self.llm_analyzer is None:
            return False, False
        elif self.is_parent_child_relation(arg_type, param_type,
                                           ori_arg_type_name, ori_param_type_name):
            return True, True
        return False, True

    # 确认类型1是否可能包含类型2
    def is_type_contain(self, type1: Tuple[str, int], type2: Tuple[str, int]) -> bool:
        # 如果type1不是结构体类型或者找不到对应的结构体定义，不予考虑
        if type1[0] not in self.collector.struct_names or \
                type1[0] not in self.collector.struct_infos.keys():
            return False
        first_field_of_type1 = self.collector.struct_first_field_types.get(type1[0],
                                                                           None)
        # 查不到第一个field的类型
        if first_field_of_type1 is None:
            return False
        src_type_name, pointer_level = parsing_type((first_field_of_type1, 0))
        src_type: Tuple[str, int] = get_original_type((src_type_name, pointer_level),
                                                      self.collector.type_alias_infos)
        # 如果第一个field的类型和type2相同
        if src_type[0] == type2[0] and src_type[1] + type1[1] == type2[1]:
            return True
        return False

    # 存在结构体类型的父类子类关系
    def is_parent_child_relation(self, type1: Tuple[str, int], type2: Tuple[str, int],
                                 ori_arg_type: str, ori_param_type: str) -> bool:
        # 必须都是指针类型
        if type1[1] == 0 or type2[1] == 0:
            return False
        # 必须都是结构体类型
        if type1[0] not in self.collector.struct_infos.keys() or \
                type2[0] not in self.collector.struct_infos.keys():
            return False
        # 如果llm已经分析过这两个类型
        if (type1[0], type2[0]) in self.llm_analyzed_types.keys():
            return self.llm_analyzed_types[(type1[0], type2[0])]
        if (type2[0], type1[0]) in self.llm_analyzed_types.keys():
            return self.llm_analyzed_types[(type2[0], type1[0])]

        arg_struct_def: str = self.collector.struct_name2declarator.get(type1[0])
        param_struct_def: str = self.collector.struct_name2declarator.get(type2[0])

        user_prompt_content = user_prompt.format(struct_type1=ori_arg_type,
            struct_type2=ori_param_type,
            struct_type1_definition=arg_struct_def,
            struct_type2_definition=param_struct_def)
        contents: List[str] = [system_prompt, user_prompt_content]
        prompt_log: str = system_prompt + "\n\n" + user_prompt_content

        yes_time = 0
        # 投票若干次
        for i in range(self.vote_time):
            answer: str = self.llm_analyzer.get_response(contents)
            prompt_log += ("\n\nvote {}:========================\n".format(i + 1) + answer)
            # 如果回答的太长了，让它summarize一下
            tokens = answer.split(' ')
            if len(tokens) >= 8:
                summarizing_text: str = summarizing_prompt.format(answer)
                answer = self.llm_analyzer.get_response([summarizing_text])
                prompt_log += "\n\nvote {}:===========================\n".format(i + 1) + summarizing_text
                prompt_log += "\n\n" + answer

            if 'yes' in answer.lower():
                yes_time += 1

        flag = (yes_time > (self.vote_time / 2))
        self.llm_analyzed_types[(type1[0], type2[0])] = flag

        # 如果需要log
        if self.log_flag:
            content: str = f"{type1[0]},{type2[0]},{ori_arg_type},{ori_param_type}:{flag}"
            open(self.log_type_alias_file, 'a', encoding='utf-8').write(content + "\n")
            prompt_file = f"{type1[0]}-{type2[0]}.txt"
            open(os.path.join(self.struct_analysis_log_path, prompt_file),'w', encoding='utf-8')\
                .write(prompt_log)
        return flag

    def match_single_declarator_text(self, func_pointer_declarator: str,
                                     func_declarator: str) -> bool:
        prompts: List[str] = [system_prompt_declarator,
                              user_prompt_declarator.format(func_pointer_declarator
                                                            ,func_declarator)]
        prompt_log: str = system_prompt_declarator + "\n\n" + \
                          user_prompt_declarator.format(func_pointer_declarator
                                                            ,func_declarator)

        yes_time: int = 0

        # 投票若干次
        for i in range(self.vote_time):
            answer: str = self.llm_analyzer.get_response(prompts)
            prompt_log += "\n\nvote {}:========================\n".format(i + 1) + answer
            # 如果回答的太长了，让它summarize一下
            tokens = answer.split(' ')
            if len(tokens) >= 8:
                answer = self.llm_analyzer.get_response([summarizing_prompt.format(answer)])
                prompt_log += "\n\nvote {}:===========================\n".format(i + 1) + summarizing_prompt.format(answer)
                prompt_log += "\n\n" + answer

            if 'yes' in answer.lower():
                yes_time += 1

        # 如果需要log
        if self.log_flag:
            size = len(os.listdir(self.declarator_analysis_log_path))
            prompt_file = f"{size + 1}.txt"
            open(os.path.join(self.declarator_analysis_log_path, prompt_file), 'w', encoding='utf-8') \
                .write(prompt_log)

        # 取多数次结果返回
        flag = (yes_time > (self.vote_time / 2))
        return flag

    # 根据形参签名匹配indirect-call对应的潜在callee
    def match_with_types(self, arg_type: List[Tuple[str, int]], callsite_key: str,
                             var_arg: bool = False):
        if callsite_key not in self.callees.keys():
            self.callees[callsite_key] = set()
        # 参数数量
        arg_num: int = len(arg_type)
        fixed_arg_type: List[Tuple[str, int]] = list()
        ori_type_names: List[str] = list()
        for arg_t in arg_type:
            src_type, pointer_level = parsing_type(arg_t)
            fixed_arg_type.append(get_original_type((src_type, pointer_level),
                                                    self.collector.type_alias_infos))
            ori_type_names.append(src_type)
        func_set: Set[str] = set()

        # 多线程实现
        def process_func_set(func_keys: Set[str],
                              cur_fixed_arg_type: List[Tuple[str, int]]):
            new_func_keys = func_keys.copy()
            # 过滤掉不在当前scope范围内的以及已经分析过的
            if self.scope_strategy is not None:
                new_func_keys = set(filter(lambda func_key:
                                            self.scope_strategy.analyze_key(callsite_key, func_key)
                                            and func_key not in self.callees[callsite_key],
                                            new_func_keys))
            lock = threading.Lock()
            executor = ThreadPoolExecutor(max_workers=self.num_worker)
            pbar = tqdm(total=len(new_func_keys), desc="matcing type for {}-th icall {}"
                        .format(self.processed_icall_num, callsite_key))
            futures = []

            def update_progress(future):
                pbar.update(1)

            def worker(func_key: str):
                # 基于callsite的形参和call target实参进行类型匹配
                param_types: List[Tuple[str, int]] = self.collector.param_types.get(func_key)
                # 原始参数类型名
                ori_param_type_names: List[str] = self.collector.ori_param_types.get(func_key)
                flag, llm_helped = self.match_types_callsite_target(cur_fixed_arg_type,
                                                                    param_types[:len(cur_fixed_arg_type)],
                                                                    ori_type_names,
                                                                    ori_param_type_names)
                # 如果匹配成功
                if flag:
                    with lock:
                        func_set.add(func_key)
                        # 如果llm帮忙了
                        if llm_helped:
                            self.llm_helped_type_analysis_icall_pair[callsite_key].add(func_key)

            for func_key in new_func_keys:
                future = executor.submit(worker, func_key)
                future.add_done_callback(update_progress)
                futures.append(future)

            for future in as_completed(futures):
                try:
                    future.result(timeout=60)
                except TimeoutError:
                    logging.info("thread time out")

        # 遍历固定参数数量的函数列表
        fixed_num_func_keys: Set[str] = self.collector.param_nums_2_func_keys.get(arg_num, {})
        process_func_set(fixed_num_func_keys, fixed_arg_type)

        # 遍历可变参数函数列表
        for param_num, func_keys in self.collector.var_arg_param_nums_2_func_keys.items():
            # 可能被调用
            if param_num <= arg_num:
                process_func_set(func_keys, fixed_arg_type[: param_num])
            # 如果indirect-callsite和call target都支持可变参数，并且target参数多于callsite
            elif var_arg and param_num > arg_num:
                process_func_set(func_keys, fixed_arg_type)

        # 如果arg_types支持可变参数
        if var_arg:
            # 遍历固定参数函数列表中形参数量大于arg_num的函数
            for param_num, func_keys in self.collector.param_nums_2_func_keys.items():
                # 可能被调用
                if param_num > arg_num:
                    process_func_set(func_keys, fixed_arg_type)

        self.callees[callsite_key].update(func_set)

    def match_with_declarator_texts(self, func_pointer_declarator: str, callsite_key: str,
                                     arg_num: int, var_arg: bool):
        if callsite_key not in self.callees.keys():
            self.callees[callsite_key] = set()

        func_set = set()
        def process_func_set(func_keys: Set[str]):
            new_func_keys = func_keys.copy()
            if self.scope_strategy is not None:
                new_func_keys = set(filter(lambda func_key:
                                           self.scope_strategy.analyze_key(callsite_key, func_key)
                                           and func_key not in self.callees[callsite_key],
                                           new_func_keys))
            # 过滤掉已经分析过declarator的
            new_func_keys = set(filter(lambda func_key:
                                        func_key not in self.llm_declarator_analysis[callsite_key],
                                        new_func_keys))
            lock = threading.Lock()
            executor = ThreadPoolExecutor(max_workers=self.num_worker)
            pbar = tqdm(total=len(new_func_keys), desc="matcing declarator for {}-th icall {}"
                        .format(self.processed_icall_num, callsite_key))
            futures = []

            def update_progress(future):
                pbar.update(1)

            def worker(func_key: str):
                # 基于callsite的形参和call target实参进行类型匹配
                function_declarator: str = self.collector.func_key_2_declarator[func_key]
                flag = self.match_single_declarator_text(func_pointer_declarator,
                                                         function_declarator)
                # 如果匹配成功
                if flag:
                    with lock:
                        func_set.add(func_key)
                        # 如果llm帮忙了
                        self.llm_declarator_analysis[callsite_key].add(func_key)

            for func_key in new_func_keys:
                future = executor.submit(worker, func_key)
                future.add_done_callback(update_progress)
                futures.append(future)

            for future in as_completed(futures):
                try:
                    future.result(timeout=60)
                except TimeoutError:
                    logging.info("thread time out")

        # 遍历固定参数数量的函数列表
        fixed_num_func_keys: Set[str] = self.collector.param_nums_2_func_keys.get(arg_num, {})
        process_func_set(fixed_num_func_keys)

        # 遍历可变参数函数列表
        for param_num, func_keys in self.collector.var_arg_param_nums_2_func_keys.items():
            # 可能被调用
            if param_num <= arg_num:
                process_func_set(func_keys)
            # 如果indirect-callsite和call target都支持可变参数，并且target参数多于callsite
            elif var_arg and param_num > arg_num:
                process_func_set(func_keys)

        # 如果arg_types支持可变参数
        if var_arg:
            # 遍历固定参数函数列表中形参数量大于arg_num的函数
            for param_num, func_keys in self.collector.param_nums_2_func_keys.items():
                # 可能被调用
                if param_num > arg_num:
                    process_func_set(func_keys)

        self.callees[callsite_key].update(func_set)