from tree_sitter import Node
from typing import Dict, List, DefaultDict, Tuple, Set
from collections import defaultdict
import logging

from code_analyzer.visit_utils.func_type import get_func_pointer_name
from code_analyzer.visit_utils.decl_util import DeclareTypeException
from code_analyzer.visitors.tree_sitter_base_visitor import ASTVisitor
from code_analyzer.schemas.enums import TypeEnum
from code_analyzer.visit_utils.decl_util import process_declarator, process_multi_var_declaration

punctuations: set = {'(', ')', ','}

# 负责第一次遍历语法树
class GlobalVisitor(ASTVisitor):
    def __init__(self, icall_infos: List[Tuple[int, int]] = []):
        self.macro_defs: Dict[str, str] = dict()
        self.macro_func_args: DefaultDict[str, List[str]] = defaultdict(list)
        self.macro_func_bodies: Dict[str, str] = dict()

        self.anonymous_struct_num: int = 0
        self.anoymous_enum_num: int = 0
        # 将每个结构体类型对应的field映射为type name
        self.struct_infos: DefaultDict[str, Dict[str, str]] = defaultdict(dict)
        # 函数指针类型定义对应的raw declarator text
        self.func_type2raw_declarator: Dict[str, str] = dict()
        # 函数指针类型对应的参数类型
        self.func_type2param_types: Dict[str, List[str]] = dict()
        # 函数指针全局变量对应的参数类型
        self.func_var2param_types: Dict[str, List[str]] = dict()
        self.enum_infos: Set[str] = set()
        # 保存类型别名信息
        self.type_alias_infos: Dict[str, str] = dict()
        # 全局变量映射为类型
        self.global_var_info: Dict[str, str] = dict()
        # 全局变量名映射为declarator text
        self.global_var_2_declarator_text: Dict[str, str] = dict()

        self.icall_infos = icall_infos
        self.arg_info_4_callsite: DefaultDict[str, Dict[Tuple[int, int],
                                          List[Tuple[str, int]]]] = defaultdict(dict)
        # 每一个indirect-call的文本s
        self.icall_nodes: DefaultDict[str, Dict[Tuple[int, int], Node]] = defaultdict(dict)

        self.current_file = ""

        # 结构体函数指针field映射到对应的声明以及参数类型
        # struct_name --> field_name --> list of param types
        self.func_struct_fields: Dict[str, Dict[str, List[str]]] = dict()
        # struct_name --> field_name --> declarator
        self.func_struct_field_declarators: Dict[str, Dict[str, str]] = dict()

        # 全局函数指针变量中支持可变参数的变量
        self.var_param_func_var: Set[str] = set()
        # 类型定义中支持可变参数的函数指针类型
        self.var_param_func_type: Set[str] = set()
        # 结构体field支持可变参数的函数指针field
        self.var_param_func_struct_fields: Dict[str, Set[str]] = dict()

        # 结构体第一个field的类型，用来作cast分析时候用, struct_name --> first field type name
        self.struct_first_field_types: Dict[str, str] = dict()


    # 全局信息获取，不访问函数定义
    def visit_function_definition(self, node: Node):
        return False

    # 处理普通宏
    def visit_preproc_def(self, node: Node):
        # 跳过空的宏定义
        if node.child_count < 4:
            return False
        if node.children[1].type != "identifier":
            return False
        # assert node.children[1].type == "identifier"
        # 也可能是comment
        if node.children[2].type != "preproc_arg":
            return False

        macro: str = node.children[1].text.decode('utf8').strip()
        preproc_arg: str = node.children[2].text.decode('utf8').strip()
        self.macro_defs[macro] = preproc_arg
        return False

    # 处理宏函数
    def visit_preproc_function_def(self, node: Node):
        # 跳过空的宏函数
        if node.child_count < 5:
            return False
        assert node.children[1].type == "identifier"
        assert node.children[2].type == "preproc_params"
        if node.children[3].type != "preproc_arg":
            return False
        macro: str = node.children[1].text.decode('utf8').strip()
        preproc_arg: str = node.children[3].text.decode('utf8').strip()
        self.macro_func_bodies[macro] = preproc_arg
        self.macro_defs[macro] = node.text.decode('utf8')

        for child in node.children[2].children:
            code: str = child.text.decode('utf8').strip()
            if code not in punctuations:
                self.macro_func_args[macro].append(code)

        return False

    # 处理类型定义
    def visit_type_definition(self, node: Node):
        assert node.child_count >= 4

        dst_declarator: Node = node.children[-2]
        try:
            suffix, _, declarator = process_declarator(dst_declarator)
        except DeclareTypeException as e:
            logging.debug("traversing node: ", node.text.decode('utf8'),
                  " location: ", node.start_point, " error")
            return False
        # 如果是函数指针定义，只记录它是个函数类型，而不指示具体类型
        if declarator.type == "function_declarator":
            dst_type: str = TypeEnum.FunctionType.value
            # assert name_node.type == "type_identifier"
            from code_analyzer.visitors.func_visitor import extract_param_types
            src_type = get_func_pointer_name(declarator, node)
            infos = extract_param_types(declarator)
            param_types: List[str] = infos[0]
            var_arg: bool = infos[1]
            if var_arg:
                self.var_param_func_type.add(src_type)
            self.func_type2param_types[src_type] = param_types
            self.func_type2raw_declarator[src_type] = node.text.decode('utf8')
        # 处理非函数指针类型
        else:
            assert declarator.type == "type_identifier"
            dst_type_node: Node = node.children[-3]
            src_type = declarator.text.decode('utf8')

            if dst_type_node.type == "struct_specifier":
                dst_type, anno_num = self.process_complex_specifier(dst_type_node,
                                        TypeEnum.StructType.value, self.anonymous_struct_num)
                self.anonymous_struct_num = anno_num
                self.process_struct_specifier(dst_type_node, dst_type)
            elif dst_type_node.type == "union_specifier":
                dst_type = "union_type"
            elif dst_type_node.type == "enum_specifier":
                # 只会记录enum的类型名，不会记录定义的enum值
                dst_type, anno_num = self.process_complex_specifier(dst_type_node,
                                        TypeEnum.EnumType.value, self.anoymous_enum_num)
                self.anoymous_enum_num = anno_num
                self.enum_infos.add(dst_type)
            else:
                dst_type = dst_type_node.text.decode('utf8')
            dst_type: str = dst_type if suffix == "" else dst_type + " " + suffix
        if src_type != dst_type:
            self.type_alias_infos[src_type] = dst_type
        return False

    def process_complex_specifier(self, dst_type_node, type_value: str, anno_num: int):
        idx = 1
        while idx < dst_type_node.child_count:
            if dst_type_node.children[idx].type == "type_identifier":
                break
            idx += 1
        # 匿名定义
        if idx >= dst_type_node.child_count:
            dst_type = type_value + str(anno_num)
            anno_num += 1
        else:
            dst_type = dst_type_node.children[idx].text.decode('utf8')
        return dst_type, anno_num

    # 处理声明
    def visit_declaration(self, node: Node):
        infos: Tuple[List[Tuple[str, str]], Dict[str, List[str]], Set[str]] \
                = process_multi_var_declaration(node)
        # 有可能是函数声明
        if len(infos) == 0:
            return False
        var_infos: List[Tuple[str, str]] = infos[0]
        func_var2param_types: Dict[str, List[str]] = infos[1]
        # 支持可变参数的全局函数指针变量
        var_arg_func_vars: Set[str] = infos[2]
        self.var_param_func_var.update(var_arg_func_vars)
        for var_info in var_infos:
            # var_info[1]为var_name, var_info[0]为var_type
            self.global_var_info[var_info[1]] = var_info[0]
            try:
                declaration_text = node.text.decode('utf8')
            except UnicodeDecodeError:
                declaration_text = node.text.decode('ISO-8859-1')
            self.global_var_2_declarator_text[var_info[1]] = declaration_text
            if var_info[1] in func_var2param_types.keys():
                self.func_var2param_types[var_info[1]] = func_var2param_types[var_info[1]]

        return False

    def visit_struct_specifier(self, node: Node):
        if node.child_count >= 3 and node.children[1].type == "type_identifier":
            type_name = node.children[1].text.decode('utf8')
            self.process_struct_specifier(node, type_name)
        return False

    def process_struct_specifier(self, node: Node, struct_name: str):
        struct_field_visitor = StructFieldVisitor()
        struct_field_visitor.traverse_node(node)
        if len(struct_field_visitor.field_name_2_type) > 0:
            self.struct_infos[struct_name] = struct_field_visitor.field_name_2_type
        # 第一个结构体field的类型
        if struct_field_visitor.first_field_type is not None:
            self.struct_first_field_types[struct_name] = struct_field_visitor.first_field_type
        # 存在函数指针field
        if len(struct_field_visitor.func_field2param_types) > 0:
            self.func_struct_fields[struct_name] = struct_field_visitor.func_field2param_types
            self.func_struct_field_declarators[struct_name] = \
                struct_field_visitor.func_field2declarator_str
        # 存在支持可变参数的函数指针field
        if len(struct_field_visitor.var_arg_func_fields) > 0:
            self.var_param_func_struct_fields[struct_name] = \
                struct_field_visitor.var_arg_func_fields

    # 处理枚举类型定义
    def visit_enum_specifier(self, node: Node):
        if node.children[1].type == "type_identifier":
            enum_type_name: str = node.children[1].text.decode('utf8')
            self.enum_infos.add(enum_type_name)


class StructFieldVisitor(ASTVisitor):
    def __init__(self):
        self.field_name_2_type: Dict[str, str] = dict()
        self.func_field2declarator_str: Dict[str, str] = dict()
        self.func_field2param_types: Dict[str, List[str]] = dict()
        self.var_arg_func_fields: Set[str] = set()
        # 结构体第一个field的类型，cast分析时会用到
        self.first_field_type: str = None

    def visit_field_declaration(self, node: Node):
        # 如果该field_declaration是union定义
        if node.children[0].type == "union_specifier":
            union_children_list: List[Node] = node.children[0].children
            for child in union_children_list:
                # 如果是field_declaration_list
                if child.type == "field_declaration_list":
                    self.traverse_node(child)
            return False
        infos: Tuple[List[Tuple[str, str]], Dict[str, List[str]], Set[str]] \
            = process_multi_var_declaration(node, True)
        # 如果是面向对象语言则可能为0
        if len(infos) == 0:
            return False
        var_infos: List[Tuple[str, str]] = infos[0]
        func_field2param_types: Dict[str, List[str]] = infos[1]
        # 支持可变参数的结构体field
        var_arg_func_fields: Set[str] = infos[2]
        self.var_arg_func_fields.update(var_arg_func_fields)
        for var_info in var_infos:
            if self.first_field_type is None:
                self.first_field_type = var_info[0]
            self.field_name_2_type[var_info[1]] = var_info[0]
            # 如果该field是函数指针定义
            if var_info[1] in func_field2param_types.keys():
                self.func_field2param_types[var_info[1]] = func_field2param_types[var_info[1]]
                self.func_field2declarator_str[var_info[1]] = node.text.decode('utf-8')
        return False


# 在全局范围内搜索函数引用
class GlobalFunctionRefVisitor(ASTVisitor):
    def __init__(self, func_set: Set[str]):
        self.func_name_set: Set[str] = func_set
        self.refered_func: Set[str] = set()

    def visit_identifier(self, node: Node):
        identifier: str = node.text.decode('utf8')
        # 引用了函数名
        if identifier in self.func_name_set:
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