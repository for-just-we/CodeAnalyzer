from code_analyzer.schemas.ast_node import ASTNode
from typing import Dict, List, Tuple, Set

from code_analyzer.visitors.base_visitor import ASTVisitor
from code_analyzer.visitors.util_visitor import CastTypeDescriptorVisitor
from code_analyzer.schemas.function_info import FuncInfo
from code_analyzer.schemas.enums import TypeEnum
from code_analyzer.visit_utils.decl_util import DeclareTypeException, process_declarator, \
    process_multi_var_declaration
from code_analyzer.visit_utils.type_util import parsing_type, get_original_type, \
    get_original_type_with_name
from code_analyzer.visit_utils.func_type import get_func_pointer_name
from code_analyzer.definition_collector import BaseInfoCollector

import logging

# 遍历函数名称和参数列表部分
class FunctionDeclaratorVisitor(ASTVisitor):
    def __init__(self, parentVisitor: 'FunctionDefVisitor', func_body: ASTNode, raw_declarator_text: str):
        self.parentVisitor: 'FunctionDefVisitor' = parentVisitor
        self.func_body: ASTNode = func_body
        self.raw_declarator_text: str = raw_declarator_text

    def visit_function_declarator(self, node: ASTNode):
        if hasattr(node, "identifier"):
            func_name: str = node.identifier.node_text
        elif hasattr(node, "qualified_identifier"):
            from code_analyzer.visitors.util_visitor import FuncNameExtractor
            func_name_extractor = FuncNameExtractor()
            func_name_extractor.traverse_node(node.qualified_identifier)
            func_name: str = func_name_extractor.identifier
            if func_name is None:
                logging.debug("parsing error in function: {}, {}".format(node.start_point, node.end_point))
                return False
        else:
            logging.debug("parsing error in function: {}, {}".format(node.start_point, node.end_point))
            return False
        # assert node.children[1].type == "parameter_list"
        parameter_visitor = ParameterListVisitor()
        self.parentVisitor.func_name_sets.add(func_name)
        func_key: str = self.parentVisitor.current_file + "<" + str(node.start_point[0] + 1)
        parameter_visitor.traverse_node(node)
        # 添加一下对va_list的处理
        func_info: FuncInfo = FuncInfo(parameter_visitor.parameter_types.copy(),
                                           parameter_visitor.name_2_declarator_text.copy(),
                                           parameter_visitor.declarator_texts.copy(),
                                           parameter_visitor.var_arg, self.raw_declarator_text,
                                           self.func_body, self.parentVisitor.current_file, func_name)
        self.parentVisitor.func_info_dict[func_key] = func_info
        # 添加支持可变参数的函数指针形参
        if len(parameter_visitor.var_arg_var_params) > 0:
            func_info.set_var_arg_func_param(parameter_visitor.var_arg_var_params)
        if len(parameter_visitor.param_name2types) > 0:
            func_info.set_func_param2param_types(parameter_visitor.param_name2types)
        if parameter_visitor.error:
            self.parentVisitor.error_funcs[func_key] = self.raw_declarator_text
        del parameter_visitor

    # 不分析函数体
    def visit_compound_statement(self, node: ASTNode):
        return False


# 只获取每个函数的签名，并保存该函数的AST
class FunctionDefVisitor(ASTVisitor):
    # 我们假定不会出现同名函数
    def __init__(self):
        self.func_info_dict: Dict[str, FuncInfo] = dict()
        self.error_funcs: Dict[str, str] = dict()
        self.current_file: str = ""
        self.func_name_sets: Set[str] = set()

    def visit_function_definition(self, node: ASTNode):
        assert hasattr(node, "compound_statement")
        func_body: ASTNode = node.compound_statement
        full_text: str = node.node_text
        func_body_text: str = func_body.node_text
        idx = full_text.find(func_body_text)
        raw_declarator_text: str = full_text[: idx]
        # 考虑到error_node存在
        declarator_visitor = FunctionDeclaratorVisitor(self, func_body, raw_declarator_text)
        declarator_visitor.traverse_node(node)

        return False

# 遍历参数列表
class ParameterListVisitor(ASTVisitor):
    def __init__(self, flag: bool = True):
        # 每个tuple为一个 (type_name, var_name) pair, 表示类型名、变量名
        self.parameter_types: List[Tuple[str, str]] = list()
        # 将形参名映射为declarator文本，比如int* p中，p的declarator为int* p
        self.name_2_declarator_text: Dict[str, str] = dict()
        self.declarator_texts: List[str] = list()
        self.var_arg: bool = False
        self.error: bool = False
        # 在解析function declarator时，如果解析的是function definition的declarator，那么当参数
        # 出现函数指针时，会进一步解析该函数指针参数的参数类型。但是，如果是类型定义或者函数参数的function declarator，
        # 遇到函数指针直接将类型标记为function declarator
        # flag为true表示遍历的是function definition，为false表示遍历的是param declaraton或者type definition
        self.flag: bool = flag
        if flag:
            self.param_name2types: Dict[str, List[str]] = dict()
            self.var_arg_var_params: Set[str] = set()


    # 处理局部变量declarator
    def process_declarator(self, declarator: ASTNode) -> Tuple[str, str, ASTNode]:
        try:
            # 寻找变量名
            suffix, declarator_text, declarator_node = process_declarator(declarator, True)
        except DeclareTypeException as e:
            raise DeclareTypeException("The type under parameter declarator should not beyond"
                                       " reference, array, pointer")
        return suffix, declarator_text, declarator_node

    # 没有默认参数
    def visit_parameter_declaration(self, node: ASTNode):
        # 如果参数类型是va_list，表示支持可变参数
        if node.children[0].node_text == "va_list":
            self.var_arg = True
            return False
        # void func(void) 属于只有1个子节点的情况，这个时候直接跳过
        if node.child_count < 2:
            type_name = node.children[0].node_text
            if type_name != "void":
                self.parameter_types.append((type_name, "_"))
            return False
        type_node: ASTNode = node.children[0]
        if type_node.node_type in {"struct_specifier", "union_specifier", "enum_specifier"}:
            type_node = type_node.children[1]
        base_type: str = type_node.node_text
        declarator: ASTNode = node.children[-1]

        try:
            # 寻找变量名
            suffix, param_name, cur_node = process_declarator(declarator, True)
            if cur_node.node_type == "function_declarator":
                param_type: str = TypeEnum.FunctionType.value
                param_name = get_func_pointer_name(cur_node, node)
                if self.flag:
                    infos = extract_param_types(cur_node)
                    param_types: List[str] = infos[0]
                    var_arg: bool = infos[1]
                    self.param_name2types[param_name] = param_types
                    # 支持可变参数
                    if var_arg:
                        self.var_arg_var_params.add(param_name)

                # param_name = name_node.text.decode('utf8')
            else:
                param_type: str = base_type if suffix == "" else base_type + " " + suffix
            self.parameter_types.append((param_type, param_name))
            self.name_2_declarator_text[param_name] = node.node_text
            self.declarator_texts.append(node.node_text)
        except DeclareTypeException as e:
            self.parameter_types.append((TypeEnum.UnknownType.value, "unknown"))
            # raise DeclareTypeException("caught Declare Type Exception")
            self.error = True
        return False

    # 有默认参数，不过benchmark中不一定有默认参数的case
    def visit_optional_parameter_declaration(self, node: ASTNode):
        assert node.child_count >= 2
        assert node.children[-2].node_text == "="
        base_type: str = node.children[0].node_text
        declarator: ASTNode = node.children[1]
        try:
            # 寻找变量名
            suffix, param_name, _ = process_declarator(declarator, True)
            param_type: str = base_type if suffix == "" else base_type + " " + suffix
            self.parameter_types.append((param_type, param_name))
        except DeclareTypeException as e:
            logging.debug("traversing node: ", node.node_text,
                  " location: ", node.start_point, " error")
            return False
        return False


    def visit(self, node: ASTNode):
        # 可变参数
        if node.node_type == "...":
            self.var_arg = True
        return True

    def visit_variadic_parameter(self, node: ASTNode):
        self.var_arg = True
        return False

def extract_param_types(declarator: ASTNode) -> Tuple[List[str], bool]:
    param_visitor: ParameterListVisitor = ParameterListVisitor(False)
    param_visitor.traverse_node(declarator)
    param_types: List[str] = list(map(lambda t: t[0], param_visitor.parameter_types))

    return param_types, param_visitor.var_arg


# 遍历函数体，收集icallsite的类型信息
# 需要考虑函数嵌套调用的关系
class FunctionBodyVisitor(ASTVisitor):
    def __init__(self, icall_infos: List[Tuple[int, int]],
                 arg_infos: Dict[str, str],
                 arg_declarators: Dict[str, str],
                 local_var_infos: Dict[str, str],
                 local_var2declarator: Dict[str, str],
                 collector: BaseInfoCollector):
        self.icall_infos: List[Tuple[int, int]] = icall_infos
        # 保存局部变量信息，var name --> var type
        self.local_var_infos: Dict[str, str] = local_var_infos
        self.local_var2declarator: Dict[str, str] = local_var2declarator
        # 保存参数信息
        self.arg_infos: Dict[str, str] = arg_infos
        self.arg_declarators: Dict[str, str] = arg_declarators
        self.arg_info_4_callsite: Dict[Tuple[int, int], List[Tuple[str, int]]] = dict()

        # 每一个indirect-call的文本s
        self.icall_nodes: Dict[Tuple[int, int], ASTNode] = dict()
        # 每一个indirect-call对应的函数指针声明的参数类型
        self.icall_2_decl_param_types: Dict[Tuple[int, int], List[str]] = dict()
        # 每一个indirect-call对应的函数指针声明的文本
        self.icall_2_decl_text: Dict[Tuple[int, int], str] = dict()
        # 每一个indirect-call对应的每个参数的相关declarator
        self.icall_2_arg_declarators: Dict[Tuple[int, int], List[List[str]]] = dict()
        # 每一个indirect-call对应的每个参数的相关文本
        self.icall_2_arg_texts: Dict[Tuple[int, int], List[str]] = dict()
        # 每一个indirect-call对应的文本
        self.icall_2_text: Dict[Tuple[int, int], str] = dict()
        # 每一个icall对应的argument_list文本
        self.icall_2_arg_text: Dict[Tuple[int, int], str] = dict()
        # 支持可变参数的indirect-call
        self.var_arg_icalls: Set[Tuple[int, int]] = set()

        # 保存宏函数
        self.current_macro_funcs: Dict[Tuple[int, int], str] = dict()
        self.collector: BaseInfoCollector = collector

    def set_func_var2param_types(self, func_var2param_types: Dict[str, List[str]]):
        self.func_var2param_types: Dict[str, List[str]] = func_var2param_types

    def set_func_param2param_types(self, func_param2param_types: Dict[str, List[str]]):
        self.func_param2param_types: Dict[str, List[str]] = func_param2param_types

    def set_var_arg_func_param(self, var_arg_func_param: Set[str]):
        self.var_arg_func_param: Set[str] = var_arg_func_param

    def set_var_arg_func_var(self, var_arg_func_var: Set[str]):
        self.var_arg_func_var: Set[str] = var_arg_func_var


    # 这个函数是考虑到函数指针类型可能存在传递关系，比如
    # typedef int(*add)(int, int);
    # typedef add add_t;
    # 在解析add_t的函数指针类型的时候需要先链接到add
    # 这里我假设函数指针类型传递不存在指针关系。
    def get_original_func_type(self, type_name: str) -> Tuple[str, bool]:
        while type_name in self.collector.type_alias_infos.keys():
            if type_name in self.collector.func_type2param_types.keys():
                return (type_name, True)
            type_name = self.collector.type_alias_infos[type_name]
        return (type_name, False)


    def visit_call_expression(self, node: ASTNode):
        if not node.start_point in self.icall_infos:
            return True
        # 为宏函数
        if node.children[0].node_type == "identifier":
            call_expr_str = node.children[0].node_text
            if call_expr_str in self.collector.macro_funcs:
                self.current_macro_funcs[node.start_point] = call_expr_str
        # 解析函数指针变量的类型
        assert hasattr(node, "argument_list")
        self.icall_2_text[node.start_point] = node.node_text
        self.icall_2_arg_text[node.start_point] = node.argument_list.node_text
        # 解析callee expression
        type_name, pointer_level = self.process_argument(node.children[0], 0, node.start_point)
        type_name, pointer_level = parsing_type((type_name, pointer_level))

        potential_func_type_name, flag = self.get_original_func_type(type_name)
        # 当前callee expression一定是函数指针，
        # 但是如果type_name不是function_type说明函数类型被typedef
        if type_name != TypeEnum.FunctionType.value \
                and flag:
            self.icall_2_decl_param_types[node.start_point] = \
                    self.collector.func_type2param_types[potential_func_type_name]
            self.icall_2_decl_text[node.start_point] = self.collector. \
                                func_type2raw_declarator[potential_func_type_name]
        # 解析argument_list
        arg_type_infos, all_arg_decls, all_arg_texts = self.process_argument_list(node.argument_list)
        self.icall_2_arg_texts[node.start_point] = all_arg_texts
        self.arg_info_4_callsite[node.start_point] = arg_type_infos
        self.icall_2_arg_declarators[node.start_point] = all_arg_decls
        self.icall_nodes[node.start_point] = node
        return True

    def process_argument_list(self, node: ASTNode) -> Tuple[List[Tuple[str, int]],
                                                            List[List[str]],
                                                            List[str]]:
        if node.child_count == 0:
            return [], [], []
        arg_type_infos: List[Tuple[str, int]] = list()
        cur_arg_idx = 0

        all_arg_decls: List[List[str]] = list()
        all_arg_texts: List[str] = list()

        while cur_arg_idx < node.child_count:
            # 需要考虑ERROR情况
            if node.children[cur_arg_idx].node_type == "ERROR":
                cur_arg_idx += 1
                continue
            # 返回type, pointer level
            type_info: Tuple[str, int] = self.process_argument(node.children[cur_arg_idx], 0)
            decls: List[str] = self.extract_decl_context(node.children[cur_arg_idx])
            arg_text: str = node.children[cur_arg_idx].node_text
            all_arg_texts.append(arg_text)
            all_arg_decls.append(decls)
            arg_type_infos.append(type_info)
            cur_arg_idx += 1
        return arg_type_infos, all_arg_decls, all_arg_texts

    # 处理函数调用的实参数，返回实际参数的base type和pointer level，
    # 如果base type = char*, pointer level = 1 , final type = char**
    # 如果base type = char*, pointer level = -1, final type = char
    def process_argument(self, node: ASTNode, pointer_level: int, icall_loc:
                Tuple[int, int] = None) -> Tuple[str, int]:
        if node.node_type == "identifier":
            def get_base_type(var_name: str, source_dict: Dict[str, str],
                              param_types_dict: Dict[str, List[str]] = None,
                              var_arg_func_vars: Set[str] = None,
                              func_var2declarator: Dict[str, str] = None) -> str:
                base_type: str = source_dict.get(var_name, TypeEnum.UnknownType.value)
                if base_type == TypeEnum.FunctionType.value and param_types_dict is not None:
                    param_types = param_types_dict.get(var_name, None)
                    if param_types is not None and icall_loc is not None:
                        self.icall_2_decl_param_types[icall_loc] = param_types
                    # 支持可变参数
                    if var_arg_func_vars is not None and var_name in var_arg_func_vars \
                            and icall_loc is not None:
                        self.var_arg_icalls.add(icall_loc)

                # 必须是函数变量
                if func_var2declarator is not None and var_name in func_var2declarator.keys() \
                        and icall_loc is not None and base_type == TypeEnum.FunctionType.value:
                    self.icall_2_decl_text[icall_loc] = func_var2declarator[var_name]
                return base_type

            var_name: str = node.node_text
            # 局部变量
            if var_name in self.local_var_infos.keys():
                func_var2param_types: Dict[str, List[str]] = \
                    getattr(self, "func_var2param_types", None)
                var_arg_func_var: Set[str] = getattr(self, "var_arg_func_var", None)
                base_type_name = get_base_type(var_name, self.local_var_infos, func_var2param_types,
                                               var_arg_func_var,
                                               self.local_var2declarator)
            # 函数形参
            elif var_name in self.arg_infos.keys():
                func_param2param_types: Dict[str, List[str]] = \
                    getattr(self, "func_param2param_types", None)
                var_arg_func_param: Set[str] = getattr(self, "var_arg_func_param", None)
                base_type_name = get_base_type(var_name, self.arg_infos, func_param2param_types,
                                               var_arg_func_param,
                                               self.arg_declarators)
            # 全局变量
            elif var_name in self.collector.global_var_info.keys():
                base_type_name = get_base_type(var_name, self.collector.global_var_info,
                                          self.collector.func_var2param_types,
                                               self.collector.var_arg_func_vars,
                                               self.collector.global_var_2_declarator_text)
            # 未知类型变量
            else:
                base_type_name = TypeEnum.UnknownType.value
            return (base_type_name, pointer_level)
        elif node.node_type == "char_literal":
            return ("char", 0)
        elif node.node_type == "string_literal":
            return ("char", 1)
        # 数组访问
        elif node.node_type == "subscript_expression":
            pointer_level -= 1
            return self.process_argument(node.children[0], pointer_level, icall_loc)
        # 指针访问
        elif node.node_type == "pointer_expression":
            if hasattr(node, "&"):
                pointer_level += 1
            elif hasattr(node, "*"):
                pointer_level -= 1
            return self.process_argument(node.children[1], pointer_level, icall_loc)
        # 结构体访问
        elif node.node_type == "field_expression":
            assert node.child_count == 3
            base_type: Tuple[str, int] = self.process_argument(node.children[0], 0, icall_loc)
            # 如果解不出base的类型，那么返回未知
            if base_type[0] == TypeEnum.UnknownType.value:
                return (TypeEnum.UnknownType.value, 0)
            # 假定src_type一定指向一个结构体类型
            src_type: Tuple[str, int] = parsing_type(base_type)
            original_src_type, _ = get_original_type(src_type,
                                                     self.collector.type_alias_infos)
            # 如果其类型不在已知结构体类型中，直接返回未知
            if original_src_type not in self.collector.struct_infos.keys():
                return (TypeEnum.UnknownType.value, 0)
            field_name_2_type: Dict[str, str] = self.collector.struct_infos[original_src_type]
            # 如果找不到当前field信息，返回未知
            assert node.children[2].node_type == "field_identifier"
            field_name: str = node.children[2].node_text
            if field_name not in field_name_2_type.keys():
                return (TypeEnum.UnknownType.value, 0)
            field_type_name: str = field_name_2_type.get(field_name)
            field_type: Tuple[str, int] = get_original_type_with_name(
                field_type_name, self.collector.type_alias_infos)

            # 如何当前field是function type,
            # icall_loc不为None表示当前访问的是call expression的callee不是argument
            if icall_loc is not None and \
                field_type_name == TypeEnum.FunctionType.value:
                # struct name为original_src_type
                param_types: List[str] = self.collector.func_struct_fields.get(
                    original_src_type, {}).get(field_name, None)
                if param_types is not None:
                    self.icall_2_decl_param_types[icall_loc] = param_types
                func_declarator: str = self.collector.struct_field_declarators\
                    .get(original_src_type,{}).get(field_name, None)
                if func_declarator is not None:
                    self.icall_2_decl_text[icall_loc] = func_declarator

                # 该field是否支持可变参数
                var_arg_fields: Set[str] = self.collector.var_arg_struct_fields.\
                    get(original_src_type, set())
                if field_name in var_arg_fields:
                    self.var_arg_icalls.add(icall_loc)

            f_type = field_type[0]
            if f_type == TypeEnum.FunctionType.value and f_type != field_type_name:
                f_type = field_type_name
            return (f_type, field_type[1] + pointer_level)

        # 类型转换
        elif node.node_type == "cast_expression":
            assert node.child_count == 2
            assert hasattr(node, "type_descriptor")
            descriptor_visitor = CastTypeDescriptorVisitor()
            descriptor_visitor.traverse_node(node.type_descriptor)
            src_type: Tuple[str, int] = get_original_type((descriptor_visitor.type_name,
                                                    descriptor_visitor.pointer_level),
                                                   self.collector.type_alias_infos)
            return src_type
        # 括号表达式
        elif node.node_type == "parenthesized_expression":
            assert node.child_count == 1
            return self.process_argument(node.children[0], pointer_level, icall_loc)
        # 其它复杂表达式
        else:
            return (TypeEnum.UnknownType.value, 0)

    # 提取每个实参表达式对应变量的context
    def extract_decl_context(self, node: ASTNode) -> List[str]:
        if node.node_type == "identifier":
            var_name: str = node.node_text
            # 局部变量
            if var_name in self.local_var_infos.keys():
                return [self.local_var2declarator[var_name]]
            # 形参
            elif var_name in self.arg_infos.keys():
                return [self.arg_declarators[var_name]]
            # 全局变量
            elif var_name in self.collector.global_var_info.keys():
                return [self.collector.global_var_2_declarator_text[var_name]]
            # 宏定义
            elif var_name in self.collector.macro_defs.keys():
                return [self.collector.macro_defs[var_name]]
            return []
        elif node.node_type == "subscript_expression":
            return self.extract_decl_context(node.children[0])
        elif node.node_type == "pointer_expression":
            return self.extract_decl_context(node.children[1])
        elif node.node_type == "field_expression":
            assert node.child_count == 3
            base_type: Tuple[str, int] = self.process_argument(node.children[0], 0, None)
            # 如果解不出base的类型，那么返回未知
            if base_type[0] == TypeEnum.UnknownType.value:
                return []
            # 假定src_type一定指向一个结构体类型
            src_type: Tuple[str, int] = parsing_type(base_type)
            original_src_type, _ = get_original_type(src_type,
                                                     self.collector.type_alias_infos)
            # 如果其类型不在已知结构体类型中，直接返回未知
            if original_src_type not in self.collector.struct_infos.keys():
                return []
            field_name_2_type: Dict[str, str] = self.collector.struct_field_declarators[original_src_type]
            # 如果找不到当前field信息，返回未知
            assert node.children[2].node_type == "field_identifier"
            field_name: str = node.children[2].node_text
            if field_name not in field_name_2_type.keys():
                return []
            return [field_name_2_type.get(field_name)]
        else:
            decls: List[str] = []
            for child in node.children:
                decls.extend(self.extract_decl_context(child))
            return decls


# 遍历函数体，收集函数体中的局部遍量定义
class LocalVarVisitor(ASTVisitor):
    def __init__(self, global_visitor=None):
        self.local_var_infos: Dict[str, str] = dict()
        # 局部变量名映射为declarator
        self.local_var_2_declarator_text: Dict[str, str] = dict()
        # 函数指针局部变量映射为参数类型
        self.func_var2param_types: Dict[str, List[str]] = dict()
        # 局部变量中支持可变参数的函数指针
        self.local_var_param_var_arg: Set[str] = set()
        self.global_visitor = global_visitor

    def visit_declaration(self, node: ASTNode):
        infos: Tuple[List[Tuple[str, str]], Dict[str, List[str]], Set[str]] \
            = process_multi_var_declaration(node, global_visitor=self.global_visitor)
        # 是函数声明
        if len(infos) == 0:
            return
        local_var_infos: List[Tuple[str, str]] = infos[0]
        func_var2param_types: Dict[str, List[str]] = infos[1]
        var_arg_var_funcs: Set[str] = infos[2]
        self.local_var_param_var_arg.update(var_arg_var_funcs)
        for var_info in local_var_infos:
            self.local_var_infos[var_info[1]] = var_info[0]
            self.local_var_2_declarator_text[var_info[1]] = node.node_text
            if var_info[1] in func_var2param_types.keys():
                self.func_var2param_types[var_info[1]] = func_var2param_types[var_info[1]]
        return False

# 遍历函数体，收集函数体中被引用的函数
class LocalFunctionRefVisitor(ASTVisitor):
    def __init__(self, func_set: Set[str], local_vars: Set[str], arg_names: Set[str],
                 refered_funcs: Set[str], macro_dict: Dict[str, str]):
        self.func_set: Set[str] = func_set
        self.local_vars: Set[str] = local_vars
        self.arg_names: Set[str] = arg_names
        self.refered_func: Set[str] = refered_funcs
        self.macro_dict: Dict[str, str] = macro_dict

    def visit_identifier(self, node: ASTNode):
        identifier: str = node.node_text

        # 引用了函数名或者通过宏定义引用函数名
        func_name = identifier
        flag = identifier in self.func_set

        if not flag and identifier in self.macro_dict:
            func_name = self.macro_dict[identifier].strip()
            flag = func_name in self.func_set
        # 引用的是函数名而不是局部变量名，这里我们假设局部变量和函数重名时会优先引用局部变量
        if flag and identifier not in self.local_vars and\
            identifier not in self.arg_names:
            # 不是直接函数调用
            if not (node.parent.node_type == "call_expression" and node == node.parent.children[0]):
                self.refered_func.add(func_name)

    def visit_function_declarator(self, node: ASTNode):
        return False

    def visit_function_definition(self, node: ASTNode):
        return False

    # 不考虑宏定义
    def visit_preproc_def(self, node: ASTNode):
        return False