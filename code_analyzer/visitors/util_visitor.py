from code_analyzer.visitors.base_visitor import ASTVisitor
from code_analyzer.schemas.ast_node import ASTNode
from code_analyzer.definition_collector import BaseInfoCollector
from code_analyzer.schemas.enums import TypeEnum
from code_analyzer.schemas.function_info import FuncInfo
from code_analyzer.visit_utils.type_util import parsing_type, get_original_type, \
    get_original_type_with_name
from code_analyzer.preprocessor.node_processor import processor
from code_analyzer.macro_expand import MacroCallExpandUtil
from code_analyzer.config import parser

from typing import Tuple, Dict, Set, List
from tree_sitter import Tree

class IdentifierExtractor(ASTVisitor):
    def __init__(self):
        self.var_name: str = ""
        self.suffix: str = ""
        self.is_function_type: bool = False
        self.is_function: bool = False

    def visit_pointer_declarator(self, node: ASTNode):
        self.suffix += "*"
        return True

    def visit_array_declarator(self, node: ASTNode):
        self.suffix += "*"
        return True

    def visit_identifier(self, node: ASTNode):
        if self.var_name == "":
            self.var_name = node.node_text
        return False

    def visit_function_declarator(self, node: ASTNode):
        # 如果是int (*add)() 则为函数指针变量
        if node.children[0].node_type == "parenthesized_declarator":
            self.is_function_type = True
        # 不然就是函数声明
        else:
            self.is_function = True
        return True

    def visit_parameter_list(self, node: ASTNode):
        return False

class FuncNameExtractor(ASTVisitor):
    def __init__(self):
        self.identifier: str = None
        self.key_node: ASTNode = None

    def visit_identifier(self, node: ASTNode):
        self.identifier = node.node_text
        self.key_node = node

    def visit_type_identifier(self, node: ASTNode):
        self.identifier = node.node_text
        self.key_node = node

    def visit_sized_type_specifier(self, node: ASTNode):
        self.identifier = node.node_text
        self.key_node = node
        return False

# 这里不考虑引用：int& a，引用对应的表达式类型是reference_declarator
class DeclaratorExtractor(ASTVisitor):
    def __init__(self, find_var_name: bool=True):
        self.key_node: ASTNode = None
        self.suffix: str = ""
        # 为True表示寻找变量名identifier、为False表示寻找类型名type_identifier
        self.find_var_name: bool = find_var_name

    def visit_pointer_declarator(self, node: ASTNode):
        self.suffix += "*"
        return True

    def visit_array_declarator(self, node: ASTNode):
        self.suffix += "*"
        return True

    def visit_abstract_pointer_declarator(self, node: ASTNode):
        self.suffix += "*"
        self.key_node = node
        return True

    def visit_identifier(self, node: ASTNode):
        if self.find_var_name:
            self.key_node = node
        return False

    def visit_function_declarator(self, node: ASTNode):
        self.key_node = node
        return False

    def visit_type_identifier(self, node: ASTNode):
        if not self.find_var_name:
            self.key_node = node
        return False

    def visit_sized_type_specifier(self, node: ASTNode):
        if not self.find_var_name:
            self.key_node = node
        return False

    def visit(self, node: ASTNode):
        if node.parent.node_type == "array_declarator" and \
            node != node.parent.children[0]:
            return False
        return True

# 识别结构体定义中field的名称和类型名
class FieldIdentifierExtractor(IdentifierExtractor):
    def __init__(self):
        super().__init__()

    def visit_identifier(self, node: ASTNode):
        return False

    def visit_field_identifier(self, node: ASTNode):
        self.var_name = node.node_text
        return False

class CastTypeDescriptorVisitor(ASTVisitor):
    def __init__(self):
        self.type_name: str = ""
        self.pointer_level: int = 0

    def visit_type_identifier(self, node: ASTNode):
        self.type_name = node.node_text
        return False

    def visit_sized_type_specifier(self, node: ASTNode):
        self.type_name = node.node_text
        return False

    def visit_abstract_pointer_declarator(self, node: ASTNode):
        self.pointer_level += 1
        return True


class VarAnalyzer(ASTVisitor):
    def __init__(self, collector: BaseInfoCollector):
        self.collector: BaseInfoCollector = collector

    # return value  [struct name, var declarator], if no struct, then ""
    def analyze_var(self, node: ASTNode, func_key) -> Tuple[str, str, str, str]:
        local_var_infos: Dict[str, str] = self.collector.func_info_dict[func_key].local_var
        local_var2declarator: Dict[str, str] = self.collector.func_info_dict[func_key].local_var2declarator
        arg_infos: Dict[str, str] = {parameter_type[1]: parameter_type[0]
                                     for parameter_type in self.collector.func_info_dict[func_key].parameter_types}
        arg_declarators: Dict[str, str] = self.collector.func_info_dict[func_key] \
            .name_2_declarator_text

        base_type, pointer_level, declarator, refered_struct_name, field_name = self.process_variable(
            node, 0, local_var_infos, local_var2declarator, arg_infos, arg_declarators)

        return (declarator, refered_struct_name, base_type, field_name)


    def process_variable(self, node: ASTNode, pointer_level: int, local_var_infos: Dict[str, str],
                         local_var2declarator: Dict[str, str], arg_infos: Dict[str, str],
                         arg_declarators: Dict[str, str]) -> Tuple[str, int, str, str, str]:
        # 1: base_type name, 2.pointer level 3: declarator text, 4: struct name 5: field name
        if node.node_type == "identifier":
            def get_base_type(var_name: str, source_dict: Dict[str, str],
                              local_var2declarator: Dict[str, str] = None) -> Tuple[str, str]:
                base_type: str = source_dict.get(var_name, TypeEnum.UnknownType.value)
                base_declarator: str = local_var2declarator.get(var_name, "")
                return (base_type, base_declarator)

            var_name: str = node.node_text
            # 局部变量
            if var_name in local_var_infos.keys():
                base_type_name, base_declarator = get_base_type(var_name, local_var_infos, local_var2declarator)
            # 函数形参
            elif var_name in arg_infos.keys():
                base_type_name, base_declarator = get_base_type(var_name, arg_infos,
                                                                arg_declarators)
            # 全局变量
            elif var_name in self.collector.global_var_info.keys():
                base_type_name, base_declarator = get_base_type(var_name, self.collector.global_var_info,
                                                                self.collector.global_var_2_declarator_text)
            # 未知类型变量
            else:
                base_type_name = TypeEnum.UnknownType.value
                base_declarator = ""
            return (base_type_name, pointer_level, base_declarator, "", "")

        elif node.node_type == "char_literal":
            return ("char", 0, "", "", "")
        elif node.node_type == "string_literal":
            return ("char", 1, "", "", "")
        elif node.node_type == "concatenated_string":
            return ("char", 1, "", "", "")

        # 数组访问
        elif node.node_type == "subscript_expression":
            pointer_level -= 1
            return self.process_variable(node.children[0], pointer_level, local_var_infos,
                                         local_var2declarator, arg_infos, arg_declarators)

        # 指针访问
        elif node.node_type == "pointer_expression":
            if hasattr(node, "&"):
                pointer_level += 1
            elif hasattr(node, "*"):
                pointer_level -= 1
            return self.process_variable(node.children[1], pointer_level, local_var_infos,
                                         local_var2declarator, arg_infos, arg_declarators)

        # 括号表达式
        elif node.node_type == "parenthesized_expression":
            assert node.child_count == 1
            return self.process_variable(node.children[0], pointer_level, local_var_infos,
                                         local_var2declarator, arg_infos, arg_declarators)

        # 结构体访问
        elif node.node_type == "field_expression":
            if node.child_count != 3:
                return (TypeEnum.UnknownType.value, 0, "", "", "")
            base_type: Tuple[str, int, str, str, str] = self.process_variable(node.children[0], 0, local_var_infos,
                                         local_var2declarator, arg_infos, arg_declarators)
            # 如果解不出base的类型，那么返回未知
            if base_type[0] == TypeEnum.UnknownType.value:
                return (TypeEnum.UnknownType.value, 0, "", "", "")
            # 假定src_type一定指向一个结构体类型
            src_type: Tuple[str, int] = parsing_type((base_type[0], base_type[1]))
            original_src_type, _ = get_original_type(src_type,
                                                     self.collector.type_alias_infos)
            # 如果其类型不在已知结构体类型中，直接返回未知
            if original_src_type not in self.collector.struct_infos.keys():
                return (TypeEnum.UnknownType.value, 0, "", "", "")
            field_name_2_type: Dict[str, str] = self.collector.struct_infos[original_src_type]
            field_declarators: Dict[str, str] = self.collector.struct_field_declarators[original_src_type]
            # 如果找不到当前field信息，返回未知
            assert node.children[2].node_type == "field_identifier"
            field_name: str = node.children[2].node_text
            if field_name not in field_name_2_type.keys():
                return (TypeEnum.UnknownType.value, 0, "", "", "")
            field_type_name: str = field_name_2_type.get(field_name)
            field_declarator: str = field_declarators.get(field_name, "")

            field_type: Tuple[str, int] = get_original_type_with_name(
                field_type_name, self.collector.type_alias_infos)

            f_type = field_type[0]
            if f_type == TypeEnum.FunctionType.value and f_type != field_type_name:
                f_type = field_type_name
            return (f_type, field_type[1] + pointer_level, field_declarator, original_src_type, field_name)

        # call expression
        elif node.node_type == "call_expression":
            callee_name = node.children[0].node_text
            arg_num = node.argument_list.child_count

            callee_func_infos: List[FuncInfo] = list(filter(lambda func_info: func_info.func_name == callee_name
                                                                              and arg_num_match(arg_num, func_info),
                                                            self.collector.func_info_dict.values()))
            return_type_set: Set[Tuple[str, int]] = set()
            for func_info in callee_func_infos:
                src_type = func_info.return_type
                original_src_type, ori_pointer_level = get_original_type(src_type,
                                                                         self.collector.type_alias_infos)
                return_type_set.add((original_src_type, ori_pointer_level))

            # 有可能是宏函数
            if len(return_type_set) == 0:
                # 如果是宏函数
                if callee_name in self.collector.macro_funcs:
                    expand_util = MacroCallExpandUtil(self.collector.macro_func_bodies,
                                                      self.collector.macro_func_args,
                                                      self.collector.global_visitor.var_arg_macro_funcs)
                    code_text = expand_util.expand_macro_call(node)
                    expand_call_tree: Tree = parser.parse(code_text.encode("utf-8"))
                    expand_root_node: ASTNode = processor.visit(expand_call_tree.root_node)
                    return self.process_variable(expand_root_node, 0, local_var_infos,
                                         local_var2declarator, arg_infos, arg_declarators)
                else:
                    return (TypeEnum.UnknownType.value, 0, "", "", "")
            else:
                assert len(return_type_set) == 1
                original_src_type, ori_pointer_level = return_type_set.pop()
                return (original_src_type, ori_pointer_level, "", "", "")

        # 其它复杂表达式
        else:
            if node.child_count == 1:
                return self.process_variable(node.children[0], 0, local_var_infos,
                                         local_var2declarator, arg_infos, arg_declarators)
            else:
                return (TypeEnum.UnknownType.value, 0, "", "", "")

# 分析一个函数指针的变量
class ExprAnalyzer(ASTVisitor):
    def __init__(self):
        self.array_level = 0
        self.identifiers: List[str] = list()

    def visit_identifier(self, node: ASTNode):
        if len(self.identifiers) == 0:
            self.identifiers.append(node.node_text)
        return super().visit(node)

    def visit_subscript_expression(self, node: ASTNode):
        self.array_level += 1
        return super().visit(node)

    def visit_field_identifier(self, node: ASTNode):
        self.identifiers.append(node.node_text)
        return super().visit(node)

    def visit(self, node: ASTNode):
        if node.parent.node_type == "subscript_expression" and \
                node is not node.parent.children[0]:
            return False
        return super().visit(node)


class FuncPointerCollector(ASTVisitor):
    def __init__(self, func_pointer_param_name: str):
        self.func_pointer_param_name = func_pointer_param_name
        # addr_taken_node, top_level_node
        self.assignment_node_infos: List[Tuple[ASTNode, int, ASTNode]] = list()
        # initializer node: addr_taken_node, initializer_list, top_level_node
        self.init_node_infos: List[Tuple[ASTNode, int, ASTNode]] = list()
        # call nodes
        self.call_nodes: List[Tuple[ASTNode, int]] = list()

    def visit_identifier(self, node: ASTNode):
        identfier = node.node_text
        if identfier != self.func_pointer_param_name:
            return False
        top_level_node, idx = get_local_top_level_expr(node)
        if top_level_node is None:
            return False

        # 如果是赋值语句
        if top_level_node.node_type == "assignment_expression" or \
            (top_level_node.node_type == "conditional_expression"
             and top_level_node.node_type == "assignment_expression"):
            self.assignment_node_infos.append((node, idx, top_level_node))

        # 如果是init declarator
        elif top_level_node.node_type == "init_declarator":
            self.init_node_infos.append((node, idx, top_level_node))

        # 如果是call expression
        elif top_level_node.node_type == "call_expression":
            if idx != -1:
                self.call_nodes.append((top_level_node, idx))

        return super().visit(node)


class ConfinedFuncPointerCollector(FuncPointerCollector):
    def __init__(self, func_pointer_param_name: str):
        super().__init__(func_pointer_param_name)
        self.callsites: List[ASTNode] = list()

    def visit_call_expression(self, node: ASTNode):
        callee_expr: ASTNode = node.children[0]
        expr_analyzer = ExprAnalyzer()
        expr_analyzer.traverse_node(callee_expr)
        if len(expr_analyzer.identifiers) == 1 and \
            expr_analyzer.identifiers[0] == self.func_pointer_param_name:
            self.callsites.append(node)
        return super().visit(node)


def index_of(parent_node: ASTNode, child_node: ASTNode):
    for i, child in enumerate(parent_node.children):
        if child is child_node:
            return i
    return -1

# 全局top_level_expr
def get_top_level_expr(node: ASTNode) -> Tuple[ASTNode, int]:
    node_types: Set[str] = {"compound_statement", "function_definition",
                            "translation_unit", "if_statement", "declaration",
                            "for_statement", "while_statement",
                            "do_statement", "switch_statement",
                            "preproc_ifdef", "preproc_if", "preproc_else", "preproc_elif"}
    initializer_level = 0
    cur_node = node
    while cur_node.parent is not None and \
            cur_node.parent.node_type not in node_types:
        if cur_node.node_type == "initializer_list":
            initializer_level += 1
        elif cur_node.node_type == "sizeof_expression":
            return (None, -1)
        cur_node = cur_node.parent
    return (cur_node, initializer_level)

# 只关注declaration, assignment_expression, call_expression
def get_local_top_level_expr(node: ASTNode) -> Tuple[ASTNode, int]:
    # 通过赋值语句传播
    cur_node: ASTNode = node
    initializer_level: int = 0
    arg_idx = -1
    while cur_node is not None:
        if cur_node.node_type == "init_declarator":
            return (cur_node, initializer_level)
        elif cur_node.node_type == "assignment_expression":
            return (cur_node, initializer_level)
        elif cur_node.node_type == "call_expression":
            return (cur_node, arg_idx)
        # 出现了三目表达式
        elif cur_node.node_type == "conditional_expression" \
                and hasattr(cur_node, "assignment_expression"):
            return (cur_node, initializer_level)
        # 不应出现在sizeof(...)中
        elif cur_node.node_type in {"sizeof_expression", "binary_expression"}:
            return (None, -1)

        if cur_node.node_type == "initializer_list":
            initializer_level += 1

        if cur_node.parent is not None:
            if cur_node.parent.node_type == "argument_list":
                arg_idx = cur_node.parent.children.index(cur_node)
            # 不能作为三目表达式的第一个子节点
            elif cur_node.parent.node_type == "conditional_expression":
                child_idx = cur_node.parent.children.index(cur_node)
                if child_idx == 0:
                    return (None, -1)
        cur_node = cur_node.parent

    return (cur_node, initializer_level)

def arg_num_match(arg_num: int, func_info: FuncInfo) -> bool:
    # 如果支持可变参数，调用的参数数量应该大于形参数量
    if func_info.var_arg:
        return arg_num >= len(func_info.parameter_types)
    else:
        return arg_num == len(func_info.parameter_types)