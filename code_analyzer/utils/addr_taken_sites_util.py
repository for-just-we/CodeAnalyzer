from code_analyzer.schemas.ast_node import ASTNode
from code_analyzer.schemas.function_info import FuncInfo
from code_analyzer.visitors.util_visitor import IdentifierExtractor, VarAnalyzer, \
    get_local_top_level_expr, get_top_level_expr, arg_num_match, ConfinedFuncPointerCollector
from code_analyzer.definition_collector import BaseInfoCollector
from code_analyzer.visit_utils.type_util import parsing_type, get_original_type

from typing import DefaultDict, List, Dict, Set, Tuple
from collections import defaultdict
import random
from tqdm import tqdm

def is_addr_taken_site(node: ASTNode) -> bool:
    # 通过赋值语句传播
    cur_node: ASTNode = node
    while cur_node is not None:
        parent_node: ASTNode = cur_node.parent
        if parent_node is None:
            return False
        # 通过赋值语句传播
        if parent_node.node_type in {"init_declarator", "assignment_expression", "initializer_pair"}:
            if hasattr(parent_node, "="):
                assign_node: ASTNode = getattr(parent_node, "=")
                assign_idx: int = parent_node.children.index(assign_node)
                if parent_node.children.index(cur_node) > assign_idx:
                    return True
                else:
                    return False
            else:
                return False

        # 通过函数参数传播
        elif parent_node.node_type == "argument_list":
            return True

        # 出现了三目表达式
        elif parent_node.node_type == "conditional_expression":
            return True

        cur_node = parent_node

    return False

def extract_addr_site(refer_sites: DefaultDict[str, List[ASTNode]]):
    addr_taken_sites_: Dict[str, List[ASTNode]] = dict()
    for func_key, refer_site in refer_sites.items():
        addr_taken_sites: List[ASTNode] = list(filter(is_addr_taken_site, refer_site))
        if len(addr_taken_sites) == 0:
            continue
        addr_taken_sites_[func_key] = addr_taken_sites

    return addr_taken_sites_


end_msgs = ["\nThe information below can also help you identify the functionlity of function {}",
            "\nSummarize the purpose of the function pointer assigned by the address of function {} based on the provided information within two sentences."]
additional_template = " You may first analyze the purpose of the variable of struct {} with the struct definition and the initializer then analyze the purpose of the function pointer which may be assigned by {}."

class AddrTakenSiteRetriver:
    def __init__(self, raw_global_addr_sites: Dict[str, List[ASTNode]],
                 raw_local_addr_sites: Dict[str, Dict[str, List[ASTNode]]],
                 collector: BaseInfoCollector):
        self.collector: BaseInfoCollector = collector
        self.var_analyzer: VarAnalyzer = VarAnalyzer(collector)

        # global scope的address-taken site只需要考虑init_declarator
        self.global_addr_sites: Dict[str, List[Tuple[ASTNode, int, ASTNode]]] = dict()

        for func_name, nodes in tqdm(raw_global_addr_sites.items(), desc="collecting raw declarators", ncols=200):
            decl_nodes: List[Tuple[ASTNode, int, ASTNode]] = list()
            for node in nodes:
                top_level_node, initializer_level = get_top_level_expr(node)
                if top_level_node is None:
                    continue
                if top_level_node.node_type == "init_declarator":
                    decl_nodes.append((top_level_node, initializer_level, node))

            decl_nodes: List[Tuple[ASTNode, int, ASTNode]] = \
                list(map(lambda x: (x[0], x[1], x[2]), decl_nodes))

            if len(decl_nodes) > 0:
                self.global_addr_sites[func_name] = decl_nodes

        # local scope的address-taken site考虑init_declarator, assignment_expression, argument_list,
        # conditional_expression
        self.local_declarators: DefaultDict[str,
                    DefaultDict[str, List[Tuple[ASTNode, int, ASTNode]]]] = defaultdict(lambda: defaultdict(list))
        self.local_assignment_exprs: DefaultDict[str,
                    DefaultDict[str, List[Tuple[ASTNode, int, ASTNode]]]] = defaultdict(lambda: defaultdict(list))
        self.local_call_expr: DefaultDict[str, List[Tuple[ASTNode, int]]] = defaultdict(list)

        for func_name, node_in_func in tqdm(raw_local_addr_sites.items(), desc="collecting local declarators", ncols=200):
            for func_key, nodes in node_in_func.items():
                for node in nodes:
                    top_level_node, initializer_level = get_local_top_level_expr(node)
                    if top_level_node is None:
                        continue
                    if top_level_node.node_type == "init_declarator":
                        self.local_declarators[func_name][func_key].append((top_level_node,
                                                                            initializer_level, node))

                    elif top_level_node.node_type == "assignment_expression" or \
                        (top_level_node.node_type == "conditional_expression"
                         and hasattr(top_level_node, "assignment_expression")):
                        self.local_assignment_exprs[func_name][func_key].append((top_level_node,
                                                                                 initializer_level, node))


                    elif top_level_node.node_type == "call_expression":
                        self.local_call_expr[func_name].append((top_level_node, initializer_level))


    def group(self):
        self.init_addr_infos: DefaultDict[str, DefaultDict[Tuple[str, str],
                                           Set[Tuple[str, str, str]]]] = \
                                defaultdict(lambda: defaultdict(set))

        # global init declarator
        for func_name, declarator_infos in tqdm(self.global_addr_sites.items(), desc="grouping global declarators", ncols=200):
            for addr_taken_site_top, init_level, addr_taken_site in declarator_infos:
                top_level_var_decl = addr_taken_site_top.parent.node_text.split('=')[0]
                struct_decl, ori_var_type, init_node_text = \
                    self.retrive_info_from_declarator(addr_taken_site_top,
                                                          addr_taken_site, init_level,
                                                          self.collector.global_var_info)
                self.init_addr_infos[func_name][(struct_decl,
                                    ori_var_type)].add((init_node_text, "", top_level_var_decl))


        # local init declarator
        for func_name, local_declarator_infos in tqdm(self.local_declarators.items(), desc="grouping local declarators", ncols=200):
            for func_key, declarator_infos in local_declarator_infos.items():
                for addr_taken_site_top, init_level, addr_taken_site in declarator_infos:
                    top_level_var_decl = addr_taken_site_top.parent.node_text.split('=')[0]
                    struct_decl, ori_var_type, init_node_text = \
                        self.retrive_info_from_declarator(addr_taken_site_top,
                                                          addr_taken_site, init_level,
                                                          self.collector.func_info_dict[func_key].local_var)
                    self.init_addr_infos[func_name][(struct_decl,
                                                     ori_var_type)].add((init_node_text, func_key, top_level_var_decl))

        # assignment expression
        self.local_assignment_infos: DefaultDict[str, DefaultDict[Tuple[str, str],
                                                                  Set[Tuple[str, str, str, str]]]] = \
            defaultdict(lambda :defaultdict(set))
        for func_name, assignment_infos in tqdm(self.local_assignment_exprs.items(), desc="grouping local assignments", ncols=200):
            for func_key, assignment_info in assignment_infos.items():
                for addr_taken_site_top, init_level, addr_taken_site in assignment_info:
                    declarator, refered_struct_name, struct_decl_text, \
                    var_text, assign_node_text = self.retrive_info_from_assignment(addr_taken_site_top, func_key)
                    self.local_assignment_infos[func_name][(refered_struct_name, struct_decl_text)]\
                        .add((declarator, var_text, assign_node_text, func_key))

        # call expression
        self.call_expr_info: DefaultDict[str, DefaultDict[str, Set[Tuple[str, str]]]] = \
            defaultdict(lambda: defaultdict(set))
        self.call_expr_arg_idx: DefaultDict[str, List[Tuple[str, int, str]]] = defaultdict(list)
        for func_name, call_nodes in tqdm(self.local_call_expr.items(), desc="grouping call expressions", ncols=200):
            for call_node, arg_idx in call_nodes:
                callee_func_name = call_node.children[0].node_text
                arg_num = call_node.argument_list.child_count
                target_funcs: List[str] = list(filter(lambda func_key: self.collector.func_info_dict[func_key].func_name == callee_func_name
                                                      and arg_num_match(arg_num, self.collector.func_info_dict[func_key]),
                       self.collector.func_info_dict.keys()))

                if len(target_funcs) <= 0:
                    # 如果是宏函数
                    continue
                else:
                    target_func_key: str = random.choice(target_funcs)
                    target_func: FuncInfo = self.collector.func_info_dict[target_func_key]
                    self.call_expr_info[func_name][callee_func_name].add((call_node.node_text,
                                                        target_func.raw_declarator_text))

                    for target_func_key in target_funcs:
                        self.call_expr_arg_idx[func_name].append((target_func_key, arg_idx, call_node.node_text))

    def generate_queries_for_func(self, func_name) -> List[str]:
        queries: List[str] = list()
        # init declarator
        declarator_infos: DefaultDict[Tuple[str, str], Set[Tuple[str, str, str]]] = self.init_addr_infos[func_name]
        for decl_info, init_node_decls in declarator_infos.items():
            struct_decl, ori_var_type = decl_info
            init_node_text, func_key, top_level_var_decl = random.choice(list(init_node_decls))
            queries.append(self.generate_text_for_declarator(func_name, struct_decl,
                                              ori_var_type, init_node_text, func_key, top_level_var_decl, 1))

        # assignment expression
        assignment_infos: DefaultDict[Tuple[str, str], Set[Tuple[str, str, str, str]]] \
                        = self.local_assignment_infos[func_name]
        for struct_info, decl_infos in assignment_infos.items():
            refered_struct_name, struct_decl_text = struct_info
            declarator, var_text, assign_node_text, func_key = random.choice(list(decl_infos))
            queries.append(self.generate_text_for_assignment(func_name, declarator, refered_struct_name,
                                              struct_decl_text, var_text, assign_node_text, func_key, 1))

        # call expression
        call_expr_arg_idxs = self.call_expr_arg_idx[func_name]
        traversed_func_name_set = set()
        for func_key, arg_idx, call_node_text in call_expr_arg_idxs:
            cur_callee_func_name = self.collector.func_info_dict[func_key].func_name
            if cur_callee_func_name in traversed_func_name_set:
                continue
            traversed_func_name_set.add(self.collector.func_info_dict[func_key].func_name)
            traversed_func_names = set()

            # 根据call chain和ret message构造query
            call_chain_context: List[Tuple[str, str]] = list()
            ret_message = self.traverse_call(func_name, func_key, arg_idx, traversed_func_names,
                                call_chain_context, call_node_text)
            queries.append(self.generate_text_from_callnode_info(func_name, call_node_text, call_chain_context, ret_message, 1))

        # call_expr_info: DefaultDict[str, Set[Tuple[str, str]]] = self.call_expr_info[func_name]
        # # 从
        # for callee_func_name, call_info_texts in call_expr_info.items():
        #     call_node_text, func_declarator = random.choice(list(call_info_texts))
        #     queries.append(self.generate_text_for_callnode(func_name, call_node_text, func_declarator, 1))

        return queries

    def random_select_one(self, func_name) -> str:
        # 第3个表示作用域是否是global，否则就是local
        # 首先从全局部分筛选
        if len(self.global_addr_sites.get(func_name, [])) > 0:
            addr_taken_site_top, init_level, addr_taken_site = random.choice(self.global_addr_sites[func_name])
            top_level_var_decl = addr_taken_site_top.parent.node_text.split('=')[0]
            struct_decl, ori_var_type, init_node_text = \
                self.retrive_info_from_declarator(addr_taken_site_top,
                                                  addr_taken_site, init_level,
                                                  self.collector.global_var_info)
            return self.generate_text_for_declarator(func_name,
                                struct_decl, ori_var_type, init_node_text, "", top_level_var_decl)

        elif len(self.local_declarators[func_name]) > 0:
            func_key: str = random.choice(list(self.local_declarators[func_name].keys()))
            addr_taken_site_top, init_level, addr_taken_site \
                = random.choice(self.local_declarators[func_name][func_key])
            top_level_var_decl = addr_taken_site_top.parent.node_text.split('=')[0]
            struct_decl, ori_var_type, init_node_text = \
                self.retrive_info_from_declarator(addr_taken_site_top,
                                                  addr_taken_site, init_level,
                                                  self.collector.func_info_dict[func_key].local_var)
            return self.generate_text_for_declarator(func_name, struct_decl,
                                                     ori_var_type, init_node_text, func_key, top_level_var_decl)

        elif len(self.local_assignment_exprs[func_name]) > 0:
            func_key: str = random.choice(list(self.local_assignment_exprs[func_name].keys()))
            addr_taken_site_top, init_level, addr_taken_site \
                = random.choice(self.local_assignment_exprs[func_name][func_key])
            declarator, refered_struct_name, struct_decl_text, \
                var_text, assign_node_text = self.retrive_info_from_assignment(addr_taken_site_top, func_key)

            return self.generate_text_for_assignment(func_name, declarator, refered_struct_name, struct_decl_text,
                var_text, assign_node_text, func_key)

        elif len(self.local_call_expr[func_name]) > 0:
            call_nodes: List[Tuple[ASTNode, int]] = self.local_call_expr[func_name]
            addr_taken_site: Tuple[ASTNode, int] = random.choice(call_nodes)
            return "The address of target function {func_name} is used as a arguments of call expression: {call_expr}, " \
                   "which can also help you analyze the functionality of function {func_name}."\
                .format(func_name=func_name, call_expr=addr_taken_site[0].node_text)

        return ""

    def generate_text_for_declarator(self, func_name, struct_decl, ori_var_type, init_node_text, func_key: str, top_level_var_decl: str, stage=0) -> str:
        messages = ["The target function {func_name} is address-taken in a "
                    "initializer of a variable declaration statement, "
                    "where the declaree statement is: `{decl_stmt}`, "
                    "the initializer is\n ```c\n{initializer}\n```.".format(func_name=func_name,
                                  decl_stmt=top_level_var_decl, initializer = init_node_text)]

        additional = ""
        # 如果函数指针为结构体的一个field
        if ori_var_type != "" and struct_decl != "":
            messages.append("where the address of {func_name} is assigned to a field of struct {struct_type},"
                            " and its struct definition is:\n```c\n{struct_decl}\n```"
                            .format(func_name=func_name, struct_type=ori_var_type, struct_decl=struct_decl))
            additional = additional_template.format(ori_var_type, func_name)

        if func_key != "":
            func_info = self.collector.func_info_dict[func_key]
            cur_func_name = func_info.func_name
            func_declarator = func_info.raw_declarator_text

            messages.append("The initializer is located in function {} whose declarator is\n:`{}`"
                        .format(cur_func_name, func_declarator))

        messages.append(end_msgs[stage].format(func_name) + additional)

        return "\n\n".join(messages)

    def generate_text_for_assignment(self, func_name, declarator, refered_struct_name, struct_decl_text,
                var_text, assign_node_text, func_key, stage=0) -> str:
        messages = ["The target function {} is address-taken in a assignment expression. "
                    "The text is `{}`, where the assigned variable is {}.".format(func_name, assign_node_text, var_text)]

        additional = ""
        if declarator != "":
            messages.append("The definition of {} is {}.".format(var_text, declarator))
            if refered_struct_name != "" and struct_decl_text != "":
                messages.append("Where it is also a field of struct {}, "
                                "whose definition is: \n```\n{}\n```.".format(refered_struct_name, struct_decl_text))
                additional = additional_template.format(refered_struct_name, func_name)

        func_info = self.collector.func_info_dict[func_key]
        cur_func_name = func_info.func_name
        func_declarator = func_info.raw_declarator_text

        messages.append("The assignment expression is located in function {} whose declarator is\n:`{}`"
                        .format(cur_func_name, func_declarator))

        messages.append(end_msgs[stage].format(func_name) + additional)

        return "\n\n".join(messages)

    def generate_text_for_callnode(self, func_name, call_node_text, callee_declarator, stage=0) -> str:
        messages: List[str] = ["The address of target function {} is used as a arguments of "
                               "call expression: `{}`.".format(func_name, call_node_text)]
        if callee_declarator != "":
            messages.append("The declarator of callee function is: {}".format(callee_declarator))

        messages.append(end_msgs[stage].format(func_name))
        return "\n".join(messages)


    def generate_text_from_callnode_info(self, func_name: List[str], call_node_text: str,
                                         call_chain_context: List[Tuple[str, str]], ret_message: str,
                                         stage=0):
        messages: List[str] = ["The address of target function {} is used as a arguments of "
                               "call expression: `{}`.".format(func_name, call_node_text)]
        if len(call_chain_context) > 0:
            messages.append("Which involves a call chain as follow: ")
            for i, call_context in enumerate(call_chain_context):
                messages.append("expression of callsite-{}: `{}`\ncorresponding declarator of target function: \n```c\n{}\n```"
                                .format(i + 1, call_context[0], call_context[1]))

        if ret_message is not None:
            messages.append(ret_message)

        messages.append(end_msgs[stage].format(func_name))
        return "\n\n".join(messages)


    def retrive_info_from_declarator(self, node: ASTNode, func_node: ASTNode, initializer_level: int,
                                     var_info: Dict[str, str]):
        assert node.node_type == "init_declarator"
        # 默认取整个initializer
        init_level_in_need = initializer_level
        var_node = node.children[0]
        identifier_extractor = IdentifierExtractor()
        identifier_extractor.traverse_node(var_node)

        if identifier_extractor.is_function_type \
            or identifier_extractor.is_function:
            return ("", "", node.parent.node_text)

        var_name = identifier_extractor.var_name

        if var_name not in var_info.keys():
            return ("", "", node.parent.node_text)

        var_type = var_info[var_name]
        var_type, pointer_level = parsing_type((var_type, 0))
        ori_var_type, pointer_level = get_original_type((var_type, pointer_level),
                                                        self.collector.type_alias_infos)
        # 结构体initializer
        if ori_var_type in self.collector.struct_name2declarator.keys():
            struct_decl = self.collector.struct_name2declarator[ori_var_type]
            init_level_in_need -= pointer_level
            if init_level_in_need <= 0:
                init_level_in_need = 1
            init_node = get_init_node_for_addr_taken(func_node, init_level_in_need)
            return (struct_decl, ori_var_type, init_node.node_text)

        # 非结构体initializer
        return ("", ori_var_type, node.parent.node_text)


    def retrive_info_from_assignment(self, node: ASTNode, func_key: str):
        # c++语法可能导致错误
        if not (node.node_type == "assignment_expression" and node.child_count == 3):
            return ("", "", "", node.children[0].node_text, node.node_text)
        assert node.node_type == "assignment_expression" and node.child_count == 3
        declarator, refered_struct_name, base_type, field_name = self.var_analyzer.analyze_var(node.children[0], func_key)
        var_text = node.children[0].node_text
        struct_decl_text = ""
        if refered_struct_name != "":
            struct_decl_text = self.collector.struct_name2declarator[refered_struct_name]
        return (declarator, refered_struct_name, struct_decl_text,
                var_text, node.node_text)

    # 如果出现use case，那么生成针对1个use case的query，不为所有的use case生成query
    def traverse_call(self, func_name: str, func_key: str, idx: int, traversed_func_names: Set[str],
                      call_chain_context: List[Tuple[str, str]], cur_call_node_text):
        func_info: FuncInfo = self.collector.func_info_dict[func_key]
        if len(func_info.parameter_types) <= idx:
            return None
        # 防止递归
        if func_info.func_name in traversed_func_names:
            return None
        traversed_func_names.add(func_info.func_name)
        # 获取对应参数
        cur_declarator = func_info.raw_declarator_text
        call_chain_context.append((cur_call_node_text, cur_declarator))
        param_name = func_info.parameter_types[idx][1]
        func_pointer_collector = ConfinedFuncPointerCollector(param_name)
        func_pointer_collector.traverse_node(func_info.func_body)

        ret_message = None
        # 如果use case包含assignment
        if len(func_pointer_collector.assignment_node_infos) > 0:
            addr_taken_node, initializer_level, top_level_node = random.choice(func_pointer_collector.assignment_node_infos)
            declarator, refered_struct_name, struct_decl_text, \
                    var_text, assign_node_text = self.retrive_info_from_assignment(top_level_node, func_key)
            ret_message = self.generate_text_for_traverse_call(func_name, declarator, refered_struct_name,
                                                            struct_decl_text, var_text, assign_node_text)
            return ret_message

        # 如果use case包含直接调用
        elif len(func_pointer_collector.callsites) > 0:
            callsite: ASTNode = random.choice(func_pointer_collector.callsites)
            ret_message = "Through the call-chain, target function {} is used as a callee expression of a call expression." \
                          "The call expression is: {}".format(func_name, callsite.node_text)
            return ret_message

        # 遍历call expression
        # 随机选择一个call node展开分析
        if len(func_pointer_collector.call_nodes) > 0:
            call_node, arg_idx = random.choice(func_pointer_collector.call_nodes)
            caller_func_name = call_node.children[0].node_text
            # 需要检查是否存在宏调用
            target_func_keys: List[str] = list(
                filter(lambda func_key: self.collector.func_info_dict[func_key].func_name == caller_func_name,
                       self.collector.func_info_dict.keys()))
            if len(target_func_keys) > 0:
                cur_func_key = random.choice(target_func_keys)
                ret_message = self.traverse_call(func_name, cur_func_key, arg_idx, traversed_func_names,
                                   call_chain_context, call_node.node_text)

        return ret_message

    def generate_text_for_traverse_call(self, func_name, declarator, refered_struct_name, struct_decl_text,
                var_text, assign_node_text) -> str:
        messages = ["Through the call-chain, target function {} is used in a assignment expression. "
                    "The text is {}, where the assigned variable is {}.".format(func_name, assign_node_text, var_text)]

        if declarator != "":
            messages.append("The definition of {} is {}.".format(var_text, declarator))
            if refered_struct_name != "" and struct_decl_text != "":
                messages.append("Where it is also a field of struct {}, "
                                "whose definition is: \n{}.".format(refered_struct_name, struct_decl_text))

        return "\n".join(messages)



def get_init_node(func_node: ASTNode, level) -> ASTNode:
    cur_node = func_node
    count = 0
    while cur_node.parent.node_type != "init_declarator":
        if cur_node.node_type == "initializer_list":
            count += 1
            if count == level:
                return cur_node
        cur_node = cur_node.parent

        if cur_node.node_type == "call_expression":
            return None
    return cur_node

def get_init_node_for_addr_taken(func_node: ASTNode, level) -> ASTNode:
    cur_node = func_node
    count = 0
    while cur_node.parent.node_type != "init_declarator":
        if cur_node.node_type == "initializer_list":
            count += 1
            if count == level:
                return cur_node
        cur_node = cur_node.parent
    return cur_node