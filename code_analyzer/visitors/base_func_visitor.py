from code_analyzer.schemas.ast_node import ASTNode
from typing import Dict, List, Tuple, Set, DefaultDict
from collections import defaultdict

from code_analyzer.visitors.base_visitor import ASTVisitor

from code_analyzer.schemas.function_info import FuncInfo
from code_analyzer.schemas.enums import TypeEnum
from code_analyzer.visit_utils.decl_util import DeclareTypeException, process_declarator, \
    process_multi_var_declaration
from code_analyzer.visit_utils.func_type import get_func_pointer_name

import logging

# 遍历函数名称和参数列表部分
class FunctionDeclaratorVisitor(ASTVisitor):
    def __init__(self, parentVisitor: 'FunctionDefVisitor', func_body: ASTNode, raw_declarator_text: str, raw_return_type: str,
                 comment: str = ""):
        self.parentVisitor: 'FunctionDefVisitor' = parentVisitor
        self.func_body: ASTNode = func_body
        self.raw_declarator_text: str = raw_declarator_text
        self.raw_return_type = raw_return_type
        # 是否找到function declarator
        self.find_func_declarator = False
        self.comment = comment

    def visit_function_declarator(self, node: ASTNode):
        self.find_func_declarator = True
        if hasattr(node, "identifier"):
            func_name: str = node.identifier.node_text
        elif hasattr(node, "qualified_identifier"):
            from code_analyzer.visitors.util_visitor import FuncNameExtractor
            func_name_extractor = FuncNameExtractor()
            func_name_extractor.traverse_node(node.qualified_identifier)
            func_name: str = func_name_extractor.identifier
            if func_name is None:
                logging.getLogger("CodeAnalyzer").debug("parsing error in function: {}, {}".format(node.start_point, node.end_point))
                return False
        else:
            logging.getLogger("CodeAnalyzer").debug("parsing error in function: {}, {}".format(node.start_point, node.end_point))
            self.find_func_declarator = False
            return False
        pointer_level: int = get_pointer_level_for_return_type(node)
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
                                       self.func_body, self.parentVisitor.current_file, func_name,
                                       (self.raw_return_type, pointer_level),
                                       self.comment)
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

    def set_comment_dict(self, comment_dict: Dict[ASTNode, str]):
        self.comment_dict: Dict[ASTNode, str] = comment_dict

    def visit_function_definition(self, node: ASTNode):
        assert hasattr(node, "compound_statement")
        if not hasattr(node, "ERROR"):
            assert sum(hasattr(node, attr) for attr in
                       ["primitive_type", "type_identifier", "struct_specifier", "enum_specifier", "union_specifier",
                        "sized_type_specifier", "macro_type_specifier"]) == 1

        prim_type_values = [
            (lambda node: TypeEnum.UnknownType.value, "ERROR"),
            (lambda node: node.primitive_type.node_text, "primitive_type"),
            (lambda node: node.type_identifier.node_text, "type_identifier"),
            (lambda node: node.sized_type_specifier.node_text, "sized_type_specifier"),
            (lambda node: node.struct_specifier.type_identifier.node_text, "struct_specifier"),
            (lambda node: node.enum_specifier.type_identifier.node_text, "enum_specifier"),
            (lambda node: node.union_specifier.type_identifier.node_text, "union_specifier"),
        ]

        for value_fn, attr_name in prim_type_values:
            if hasattr(node, attr_name):
                prim_type = value_fn(node)
                break
        else:
            prim_type = TypeEnum.UnknownType.value


        func_body: ASTNode = node.compound_statement
        full_text: str = node.node_text
        func_body_text: str = func_body.node_text
        idx = full_text.find(func_body_text)
        raw_declarator_text: str = full_text[: idx]
        comment = self.comment_dict.get(node, "")
        # 考虑到error_node存在
        declarator_visitor = FunctionDeclaratorVisitor(self, func_body, raw_declarator_text, prim_type, comment)
        declarator_visitor.traverse_node(node)

        if not declarator_visitor.find_func_declarator:
            func_key: str = self.current_file + "<" + str(node.start_point[0] + 1)
            # 创建一个error function，函数名为Error!!
            func_info: FuncInfo = FuncInfo([], dict(), [],
                                           False, raw_declarator_text,
                                           func_body, self.current_file, "Error!!",
                                           (TypeEnum.UnknownType.value, 0))
            self.func_info_dict[func_key] = func_info

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
            suffix, declarator_text, declarator_node, _ = process_declarator(declarator, True)
        except DeclareTypeException as e:
            raise DeclareTypeException("The type under parameter declarator should not beyond"
                                       " reference, array, pointer")
        return suffix, declarator_text, declarator_node

    # 没有默认参数
    def visit_parameter_declaration(self, node: ASTNode):
        # 如果parameter_declaration包含ERROR node，保守策略，用uncertain处理
        if hasattr(node, "ERROR"):
            self.parameter_types.append((TypeEnum.UnknownType.value, "unknown_var"))
            self.declarator_texts.append(node.node_text)
            return False
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
            suffix, param_name, cur_node, error_flag = process_declarator(declarator, True)
            if error_flag:
                self.parameter_types.append((TypeEnum.UnknownType.value, "unknown_var"))
                self.declarator_texts.append(node.node_text)
                return False
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
            suffix, param_name, _, _ = process_declarator(declarator, True)
            param_type: str = base_type if suffix == "" else base_type + " " + suffix
            self.parameter_types.append((param_type, param_name))
        except DeclareTypeException as e:
            logging.getLogger("CodeAnalyzer").debug("traversing node: ", node.node_text,
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
        self.local_refer_sites: DefaultDict[str, List[ASTNode]] = defaultdict(list)

    def visit_identifier(self, node: ASTNode):
        if node.parent.node_type in {"init_declarator", "assignment_expression",
                                     "initializer_pair"}:
            if hasattr(node.parent, "="):
                assign_node: ASTNode = getattr(node.parent, "=")
                assign_idx: int = node.parent.children.index(assign_node)
                if node.parent.children.index(node) <= assign_idx:
                    return False

        if node.parent.node_type == "preproc_ifdef":
            return False

        if node.parent.node_type == "binary_expression" and \
            node.parent.children.index(node) <= 1:
            return False

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
            # 不是直接函数调用同时不是宏函数定义
            if not (node.parent.node_type == "call_expression" and node == node.parent.children[0]):
                self.refered_func.add(func_name)
                self.local_refer_sites[func_name].append(node)


    def visit_function_declarator(self, node: ASTNode):
        return False

    def visit_function_definition(self, node: ASTNode):
        return False

    # 不考虑宏定义
    def visit_preproc_def(self, node: ASTNode):
        return False

    def visit_preproc_function_def(self, node: ASTNode):
        return False

    def visit_preproc_defined(self, node: ASTNode):
        return False


    def visit_struct_specifier(self, node: ASTNode):
        return False

    def visit_union_specifier(self, node: ASTNode):
        return False

    def visit_enum_specifier(self, node: ASTNode):
        return False

    def visit_type_definition(self, node: ASTNode):
        return False

    def visit_declaration(self, node: ASTNode):
        if not hasattr(node, "init_declarator"):
            return False
        return super().visit(node)

    def visit_field_expression(self, node: ASTNode):
        return False

    def visit(self, node: ASTNode):
        parent_node: ASTNode = node.parent
        if parent_node is None:
            return super().visit(node)
        # 处理变量名和函数名重名的情况
        # 如果是变量定义且变量名和函数名重名
        if parent_node.node_type == "declaration":
            return super().visit(node) \
                if node.node_type == "init_declarator" \
                else False
        elif parent_node.node_type in {"init_declarator", "assignment_expression", "initializer_pair"}:
            if hasattr(parent_node, "="):
                assign_node: ASTNode = getattr(parent_node, "=")
                assign_idx: int = parent_node.children.index(assign_node)
                if parent_node.children.index(node) > assign_idx:
                    return super().visit(node)
                else:
                    return False
            else:
                return False
        else:
            return super().visit(node)


def get_pointer_level_for_return_type(node: ASTNode):
    assert node.node_type == "function_declarator"
    cur_node = node
    pointer_level = 0
    while cur_node.node_type != "function_definition":
        if cur_node.node_type in {"array_declarator", "pointer_declarator"}:
            pointer_level += 1
        cur_node = cur_node.parent
    return pointer_level




class LocalGlobalRefVisitor(ASTVisitor):
    def __init__(self, func_set: Set[str], local_vars: Set[str], arg_names: Set[str],
                 var_name: str, macro_dict: Dict[str, str]):
        self.func_set: Set[str] = func_set
        self.local_vars: Set[str] = local_vars
        self.arg_names: Set[str] = arg_names
        self.var_name: str = var_name
        self.macro_dict: Dict[str, str] = macro_dict
        self.local_refer_sites: DefaultDict[str, List[ASTNode]] = defaultdict(list)

    def visit_identifier(self, node: ASTNode):
        if node.parent.node_type in {"init_declarator", "assignment_expression",
                                     "initializer_pair"}:
            if hasattr(node.parent, "="):
                assign_node: ASTNode = getattr(node.parent, "=")
                assign_idx: int = node.parent.children.index(assign_node)
                if node.parent.children.index(node) <= assign_idx:
                    return False

        if node.parent.node_type == "preproc_ifdef":
            return False

        if node.parent.node_type == "binary_expression" and \
            node.parent.children.index(node) <= 1:
            return False

        identifier: str = node.node_text
        if identifier == self.var_name:
            self.local_refer_sites[self.var_name].append(node)


    def visit_function_declarator(self, node: ASTNode):
        return False

    def visit_function_definition(self, node: ASTNode):
        return False

    # 不考虑宏定义
    def visit_preproc_def(self, node: ASTNode):
        return False

    def visit_preproc_function_def(self, node: ASTNode):
        return False

    def visit_preproc_defined(self, node: ASTNode):
        return False

    def visit_struct_specifier(self, node: ASTNode):
        return False

    def visit_union_specifier(self, node: ASTNode):
        return False

    def visit_enum_specifier(self, node: ASTNode):
        return False

    def visit_type_definition(self, node: ASTNode):
        return False

    def visit_declaration(self, node: ASTNode):
        if not hasattr(node, "init_declarator"):
            return False
        return super().visit(node)

    def visit_field_expression(self, node: ASTNode):
        return False

    def visit(self, node: ASTNode):
        parent_node: ASTNode = node.parent
        if parent_node is None:
            return super().visit(node)
        # 处理变量名和函数名重名的情况
        # 如果是变量定义且变量名和函数名重名
        if parent_node.node_type == "declaration":
            return super().visit(node) \
                if node.node_type == "init_declarator" \
                else False
        elif parent_node.node_type in {"init_declarator", "assignment_expression", "initializer_pair"}:
            if hasattr(parent_node, "="):
                assign_node: ASTNode = getattr(parent_node, "=")
                assign_idx: int = parent_node.children.index(assign_node)
                if parent_node.children.index(node) > assign_idx:
                    return super().visit(node)
                else:
                    return False
            else:
                return False
        else:
            return super().visit(node)
