from tree_sitter import Node
from typing import Dict, List, Tuple, DefaultDict, Set

from code_analyzer.visitors.tree_sitter_base_visitor import ASTVisitor
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
    def __init__(self, parentVisitor, func_body: Node, raw_declarator_text):
        self.parentVisitor = parentVisitor
        self.func_body = func_body
        self.raw_declarator_text = raw_declarator_text

    def visit_function_declarator(self, node: Node):
        if node.children[0].type == "identifier":
            func_name_node = node.children[0]
        elif node.children[0].type == "qualified_identifier":
            assert node.children[0].children[-1].type == "identifier"
            func_name_node = node.children[0].children[-1]
        else:
            logging.debug("parsing error in function: {}, {}".format(node.start_point, node.end_point))
            return False
        # assert node.children[1].type == "parameter_list"
        parameter_visitor = ParameterListVisitor()
        func_name: str = func_name_node.text.decode('utf8')
        self.parentVisitor.func_name_sets.add(func_name)
        func_key: str = self.parentVisitor.current_file + "<" + str(node.start_point[0] + 1)
        parameter_visitor.traverse_node(node)
        # 添加一下对va_list的处理
        func_info: FuncInfo = FuncInfo(parameter_visitor.parameter_types.copy(),
                                           parameter_visitor.name_2_declarator_text.copy(),
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

    def visit_compound_statement(self, node: Node):
        return False


# 只获取每个函数的签名，并保存该函数的AST
class FunctionDefVisitor(ASTVisitor):
    # 我们假定不会出现同名函数
    def __init__(self):
        self.func_info_dict: Dict[str, FuncInfo] = dict()
        self.error_funcs: Dict[str, str] = dict()
        self.current_file: str = ""
        self.func_name_sets: Set[str] = set()

    def visit_function_definition(self, node: Node):
        assert node.children[-1].type == "compound_statement"
        raw_declarator_text = " ".join(list(map(lambda n: n.text.decode('utf8'),
                                                node.children[:-1])))
        func_body: Node = node.children[-1]
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
        self.var_arg: bool = False
        self.error: bool = False
        # 在解析function declarator时，如果解析的是function definition的declarator，那么当参数
        # 出现函数指针时，会进一步解析该函数指针参数的参数类型。但是，如果是类型定义或者函数参数的function declarator，
        # 遇到函数指针直接将类型标记为function declarator
        # flag为true表示遍历的是function definition，为false表示遍历的是param declaraton或者type definition
        self.flag = flag
        if flag:
            self.param_name2types: Dict[str, List[str]] = dict()
            self.var_arg_var_params: Set[str] = set()


    # 处理declarator
    def process_declarator(self, declarator: Node) -> Tuple[str, str, Node]:
        suffix: str = ""
        while declarator.type != "identifier" and declarator.type != "function_declarator":
            if declarator.type == "pointer_declarator":
                declarator = declarator.children[-1]
                suffix += "*"
            elif declarator.type == "reference_declarator":
                declarator = declarator.children[-1]
            # 函数形参一定是int a[]这种，不会有int[] a
            elif declarator.type == "array_declarator":
                suffix += "*"
                declarator = declarator.children[0]
            else:
                raise DeclareTypeException("The type under parameter declarator should not beyond"
                                   " reference, array, pointer")
        return suffix, declarator.text.decode('utf8'), declarator

    # 没有默认参数
    def visit_parameter_declaration(self, node: Node):
        # void func(void) 属于只有1个子节点的情况，这个时候直接跳过
        if node.child_count < 2:
            return False
        type_node: Node = node.children[-2]
        while type_node.type == "struct_specifier":
            type_node = type_node.children[1]
        base_type: str = type_node.text.decode('utf8')
        declarator: Node = node.children[-1]

        try:
            suffix, param_name, cur_node = process_declarator(declarator)
            if cur_node.type == "function_declarator":
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
            self.name_2_declarator_text[param_name] = node.text.decode('utf8')
        except DeclareTypeException as e:
            self.parameter_types.append((TypeEnum.UnknownType.value, "unknown"))
            # raise DeclareTypeException("caught Declare Type Exception")
            self.error = True
        return False

    # 有默认参数，不过benchmark中不一定有默认参数的case
    def visit_optional_parameter_declaration(self, node: Node):
        assert node.child_count >= 2
        assert node.children[-2].type == "="
        base_type: str = node.children[-4].text.decode('utf8')
        declarator: Node = node.children[-3]
        suffix, param_name, _ = process_declarator(declarator)
        param_type: str = base_type if suffix == "" else base_type + " " + suffix
        self.parameter_types.append((param_type, param_name))
        return False

    def visit(self, node: Node):
        # 可变参数
        if node.type == "...":
            self.var_arg = True
        return True

    def visit_variadic_parameter(self, node: Node):
        self.var_arg = True
        return False

def extract_param_types(declarator: Node) -> Tuple[List[str], bool]:
    param_visitor: ParameterListVisitor = ParameterListVisitor(False)
    param_visitor.traverse_node(declarator)
    param_types: List[str] = list(map(lambda t: t[0], param_visitor.parameter_types))

    return param_types, param_visitor.var_arg


# 遍历函数体，收集icallsite的类型信息
# 需要考虑函数嵌套调用的关系
class FunctionBodyVisitor(ASTVisitor):
    def __init__(self, icall_infos: List[Tuple[int, int]],
                 arg_infos: Dict[str, str],
                 local_var_infos: Dict[str, str],
                 collector: BaseInfoCollector):
        self.icall_infos: List[Tuple[int, int]] = icall_infos
        # 保存局部变量信息，var name --> var type
        self.local_var_infos: Dict[str, str] = local_var_infos
        # 保存参数信息
        self.arg_infos: Dict[str, str] = arg_infos
        self.arg_info_4_callsite: Dict[Tuple[int, int], List[Tuple[str, int]]] = dict()

        # 每一个indirect-call的文本s
        self.icall_nodes: Dict[Tuple[int, int], Node] = dict()
        # 每一个indirect-call对应的函数指针声明的参数类型
        self.icall_2_decl_param_types: Dict[Tuple[int, int], List[str]] = dict()
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

    def visit_call_expression(self, node: Node):
        if not node.start_point in self.icall_infos:
            return True
        # 为宏函数
        if node.children[0].type == "identifier":
            call_expr_str = node.children[0].text.decode('utf8')
            if call_expr_str in self.collector.macro_funcs:
                self.current_macro_funcs[node.start_point] = call_expr_str
        # 解析函数指针变量的类型
        assert node.children[-1].type == "argument_list"
        type_name, pointer_level = self.process_argument(node.children[0], 0, node.start_point)
        type_name, _ = parsing_type((type_name, pointer_level))
        # 当前callee expression一定是函数指针，
        # 但是如果type_name不是function_type说明函数类型被typedef
        if type_name != TypeEnum.FunctionType.value \
                and type_name in self.collector.func_type2param_types.keys():
            self.icall_2_decl_param_types[node.start_point] = \
                    self.collector.func_type2param_types[type_name]
        arg_type_infos: List[Tuple[str, int]] = self.process_argument_list(node.children[-1])
        self.arg_info_4_callsite[node.start_point] = arg_type_infos
        self.icall_nodes[node.start_point] = node
        return True

    def process_argument_list(self, node: Node) -> List[Tuple[str, int]]:
        assert node.children[0].type == "("
        if node.children[1].type == ")":
            return []
        arg_type_infos: List[Tuple[str, int]] = list()
        cur_arg_idx = 1

        while cur_arg_idx < node.child_count:
            # 需要考虑ERROR情况
            if node.children[cur_arg_idx].type in {",", "ERROR", ")"}:
                cur_arg_idx += 1
                continue
            # 返回type, pointer level
            type_info: Tuple[str, int] = self.process_argument(node.children[cur_arg_idx], 0)
            arg_type_infos.append(type_info)
            cur_arg_idx += 1
        return arg_type_infos

    # 处理函数调用的实参数，返回实际参数的base type和pointer level，
    # 如果base type = char*, pointer level = 1 , final type = char**
    # 如果base type = char*, pointer level = -1, final type = char
    def process_argument(self, node: Node, pointer_level: int, icall_loc:
                Tuple[int, int] = None) -> Tuple[str, int]:
        if node.type == "identifier":
            def get_base_type(var_name: str, source_dict: Dict[str, str],
                              param_types_dict: Dict[str, List[str]] = None,
                              var_arg_func_vars: Set[str] = None) -> str:
                base_type: str = source_dict.get(var_name, TypeEnum.UnknownType.value)
                if base_type == TypeEnum.FunctionType.value and param_types_dict is not None:
                    param_types = param_types_dict.get(var_name, None)
                    if param_types is not None:
                        self.icall_2_decl_param_types[icall_loc] = param_types
                    # 支持可变参数
                    if var_arg_func_vars is not None and var_name in var_arg_func_vars:
                        self.var_arg_icalls.add(icall_loc)
                return base_type

            var_name: str = node.text.decode("utf8")
            # 局部变量
            if var_name in self.local_var_infos.keys():
                func_var2param_types: Dict[str, List[str]] = \
                    getattr(self, "func_var2param_types", None)
                var_arg_func_var: Set[str] = getattr(self, "var_arg_func_var", None)
                base_type_name = get_base_type(var_name, self.local_var_infos, func_var2param_types,
                                               var_arg_func_var)
            # 函数形参
            elif var_name in self.arg_infos.keys():
                func_param2param_types: Dict[str, List[str]] = \
                    getattr(self, "func_param2param_types", None)
                var_arg_func_param: Set[str] = getattr(self, "var_arg_func_param", None)
                base_type_name = get_base_type(var_name, self.arg_infos, func_param2param_types,
                                               var_arg_func_param)
            # 全局变量
            elif var_name in self.collector.global_var_info.keys():
                base_type_name = get_base_type(var_name, self.collector.global_var_info,
                                          self.collector.func_var2param_types,
                                               self.collector.var_arg_func_vars)
            # 未知类型变量
            else:
                base_type_name = TypeEnum.UnknownType.value
            return (base_type_name, pointer_level)
        elif node.type == "char_literal":
            return ("char", 0)
        elif node.type == "string_literal":
            return ("char", 1)
        # 数组访问
        elif node.type == "subscript_expression":
            pointer_level -= 1
            return self.process_argument(node.children[0], pointer_level, icall_loc)
        # 指针访问
        elif node.type == "pointer_expression":
            if node.children[0].type == "&":
                pointer_level += 1
            elif node.children[0].type == "*":
                pointer_level -= 1
            return self.process_argument(node.children[1], pointer_level, icall_loc)
        # 结构体访问
        elif node.type == "field_expression":
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
            assert node.children[2].type == "field_identifier"
            field_name: str = node.children[2].text.decode('utf8')
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
        elif node.type == "cast_expression":
            assert node.child_count == 4
            assert node.children[1].type == "type_descriptor"
            descriptor_visitor = CastTypeDescriptorVisitor()
            descriptor_visitor.traverse_node(node.children[1])
            src_type: Tuple[str, int] = get_original_type((descriptor_visitor.type_name,
                                                    descriptor_visitor.pointer_level),
                                                   self.collector.type_alias_infos)
            return src_type
        # 括号表达式
        elif node.type == "parenthesized_expression":
            assert node.child_count == 3
            return self.process_argument(node.children[1], pointer_level, icall_loc)
        # 其它复杂表达式
        else:
            return (TypeEnum.UnknownType.value, 0)

# 遍历函数体，收集函数体中的局部遍量定义
class LocalVarVisitor(ASTVisitor):
    def __init__(self):
        self.local_var_infos: Dict[str, str] = dict()
        # 局部变量名映射为declarator
        self.local_var_2_declarator_text: Dict[str, str] = dict()
        # 函数指针局部变量映射为参数类型
        self.func_var2param_types: Dict[str, List[str]] = dict()
        # 局部变量中支持可变参数的函数指针
        self.local_var_param_var_arg: Set[str] = set()

    def visit_declaration(self, node: Node):
        infos: Tuple[List[Tuple[str, str]], Dict[str, List[str]], Set[str]] \
            = process_multi_var_declaration(node)
        # 是函数声明
        if len(infos) == 0:
            return
        local_var_infos: List[Tuple[str, str]] = infos[0]
        func_var2param_types: Dict[str, List[str]] = infos[1]
        var_arg_var_funcs: Set[str] = infos[2]
        self.local_var_param_var_arg.update(var_arg_var_funcs)
        for var_info in local_var_infos:
            self.local_var_infos[var_info[1]] = var_info[0]
            self.local_var_2_declarator_text[var_info[1]] = node.text.decode('utf8')
            if var_info[1] in func_var2param_types.keys():
                self.func_var2param_types[var_info[1]] = func_var2param_types[var_info[1]]
        return False

# 遍历函数体，收集函数体中被引用的函数
class LocalFunctionRefVisitor(ASTVisitor):
    def __init__(self, func_set: Set[str], local_vars: Set[str], arg_names: Set[str],
                 refered_funcs: Set[str]):
        self.func_set: Set[str] = func_set
        self.local_vars: Set[str] = local_vars
        self.arg_names: Set[str] = arg_names
        self.refered_func: Set[str] = refered_funcs

    def visit_identifier(self, node: Node):
        identifier: str = node.text.decode('utf8')
        # 引用的是函数名而不是局部变量名，这里我们假设局部变量和函数重名时会优先引用局部变量
        if identifier in self.func_set and identifier not in self.local_vars and\
            identifier not in self.arg_names:
            # 不是直接函数调用
            if not (node.parent.type == "call_expression" and node == node.parent.children[0]):
                self.refered_func.add(identifier)

    def visit_function_declarator(self, node: Node):
        return False

    def visit_function_definition(self, node: Node):
        return False

    # 不考虑宏定义
    def visit_preproc_def(self, node: Node):
        return False