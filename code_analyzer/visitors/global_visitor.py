from code_analyzer.schemas.ast_node import ASTNode
from typing import Dict, List, DefaultDict, Tuple, Set
from collections import defaultdict
import logging

from code_analyzer.visit_utils.func_type import get_func_pointer_name
from code_analyzer.visit_utils.decl_util import DeclareTypeException
from code_analyzer.visitors.base_visitor import ASTVisitor
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
        # 将结构体name映射到declarator
        self.struct_name2declarator: Dict[str, str] = dict()
        #
        self.struct_names: Set[str] = set()
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
        self.icall_nodes: DefaultDict[str, Dict[Tuple[int, int], ASTNode]] = defaultdict(dict)

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
    def visit_function_definition(self, node: ASTNode):
        return False

    # 处理普通宏
    def visit_preproc_def(self, node: ASTNode):
        # 跳过空的宏定义
        if not (hasattr(node, "identifier") and hasattr(node, "preproc_arg")):
            return False
        macro: str = node.identifier.node_text
        preproc_arg: str = node.preproc_arg.node_text
        self.macro_defs[macro] = preproc_arg
        return False

    # 处理宏函数
    def visit_preproc_function_def(self, node: ASTNode):
        # 跳过空的宏函数
        if not (hasattr(node, "identifier") and hasattr(node, "preproc_params")
            and hasattr(node, "preproc_arg")):
            return False
        macro: str = node.identifier.node_text
        preproc_arg: str = node.preproc_arg.node_text
        self.macro_func_bodies[macro] = preproc_arg
        self.macro_defs[macro] = node.node_text

        for child in node.preproc_params.children:
            code: str = child.node_text
            self.macro_func_args[macro].append(code)
        return False

    # 处理类型定义
    def visit_type_definition(self, node: ASTNode):
        # 可能会有一个类型定义定义多个类型
        assert node.child_count >= 2
        dst_type_node: ASTNode = node.children[0]
        # 先计算dst类型
        # 同等对待struct和union
        if dst_type_node.node_type in {"struct_specifier", "union_specifier"}:
            dst_type, anno_num = self.process_complex_specifier(dst_type_node,
                                                                TypeEnum.StructType.value, self.anonymous_struct_num)
            self.anonymous_struct_num = anno_num
            self.process_struct_specifier(dst_type_node, dst_type)
            if dst_type_node.node_type == "struct_specifier":
                self.struct_names.add(dst_type)
        elif dst_type_node.node_type == "enum_specifier":
            # 只会记录enum的类型名，不会记录定义的enum值
            dst_type, anno_num = self.process_complex_specifier(dst_type_node,
                                                                TypeEnum.EnumType.value, self.anoymous_enum_num)
            self.anoymous_enum_num = anno_num
            self.enum_infos.add(dst_type)
        else:
            dst_type = dst_type_node.node_text

        dst_declarators: List[ASTNode] = node.children[1:]
        for dst_declarator in dst_declarators:
            try:
                # 寻找类型名
                suffix, _, declarator = process_declarator(dst_declarator, False)
            except DeclareTypeException as e:
                logging.debug("traversing node: ", node.node_text,
                    " location: ", node.start_point, " error")
                return False
            # 如果是函数指针定义，只记录它是个函数类型，而不指示具体类型
            if declarator.node_type == "function_declarator":
                cur_dst_type: str = TypeEnum.FunctionType.value
                from code_analyzer.visitors.func_visitor import extract_param_types
                src_type = get_func_pointer_name(declarator, node)
                infos = extract_param_types(declarator)
                param_types: List[str] = infos[0]
                var_arg: bool = infos[1]
                if var_arg:
                    self.var_param_func_type.add(src_type)
                self.func_type2param_types[src_type] = param_types
                self.func_type2raw_declarator[src_type] = node.node_text
            # 处理非函数指针类型
            else:
                assert declarator.node_type == "type_identifier"
                src_type = declarator.node_text
                cur_dst_type: str = dst_type if suffix == "" else dst_type + " " + suffix
            if src_type != cur_dst_type:
                self.type_alias_infos[src_type] = cur_dst_type
        return False

    def process_complex_specifier(self, dst_type_node: ASTNode, type_value: str, anno_num: int):
        # 非匿名定义
        if hasattr(dst_type_node, "type_identifier"):
            dst_type = dst_type_node.type_identifier.node_text
        # 匿名定义
        else:
            dst_type = type_value + str(anno_num)
            anno_num += 1
        return dst_type, anno_num

    # 处理声明
    def visit_declaration(self, node: ASTNode):
        infos: Tuple[List[Tuple[str, str]], Dict[str, List[str]], Set[str]] \
                = process_multi_var_declaration(node, global_visitor=self)
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
            declaration_text = node.node_text
            self.global_var_2_declarator_text[var_info[1]] = declaration_text
            if var_info[1] in func_var2param_types.keys():
                self.func_var2param_types[var_info[1]] = func_var2param_types[var_info[1]]

        return False

    # 结构体类型声明，不在declaration以及typedef中
    def visit_struct_specifier(self, node: ASTNode):
        # node.child_count >= 3确保不是匿名结构体以及有field_declaration_list
        if node.child_count >= 3 and hasattr(node, "type_identifier"):
            type_name = node.type_identifier.node_text
            self.process_struct_specifier(node, type_name)
            self.struct_names.add(type_name)
        return False

    # 联合体类型声明，不在declaration以及typedef中
    def visit_union_specifier(self, node: ASTNode):
        # type_identifier确保不是匿名联合体，child_count >=3 确保有field_declaration
        if node.child_count >= 3 and hasattr(node, "type_identifier"):
            type_name = node.type_identifier.node_text
            self.process_struct_specifier(node, type_name)
        return False


    def process_struct_specifier(self, node: ASTNode, struct_name: str):
        struct_field_visitor = StructFieldVisitor(self)
        struct_field_visitor.traverse_node(node)
        # 是结构体定义而不是结构体声明
        if len(struct_field_visitor.field_name_2_type) > 0:
            self.struct_infos[struct_name] = struct_field_visitor.field_name_2_type
            self.struct_name2declarator[struct_name] = node.node_text
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
    def visit_enum_specifier(self, node: ASTNode):
        # 不是匿名枚举
        if hasattr(node, "type_identifier"):
            enum_type_name: str = node.type_identifier.node_text
            self.enum_infos.add(enum_type_name)


class StructFieldVisitor(ASTVisitor):
    def __init__(self, global_visitor=None):
        self.field_name_2_type: Dict[str, str] = dict()
        self.func_field2declarator_str: Dict[str, str] = dict()
        self.func_field2param_types: Dict[str, List[str]] = dict()
        self.var_arg_func_fields: Set[str] = set()
        # 结构体第一个field的类型，cast分析时会用到
        self.first_field_type: str = None
        self.global_visitor = global_visitor

    def visit_field_declaration(self, node: ASTNode):
        # 如果该field_declaration是union或者struct定义同时没有定义field，
        # 比如 struct A { union { int a; char b; }};
        # 中没有给union定义相应field，因此a直接通过上层结构体访问
        if node.children[0].node_type in {"union_specifier", "struct_specifier"} \
                and node.child_count == 1:
            if hasattr(node.children[0], "field_declaration_list"):
                self.traverse_node(node.children[0].field_declaration_list)
            return False
        infos: Tuple[List[Tuple[str, str]], Dict[str, List[str]], Set[str]] \
            = process_multi_var_declaration(node, True, self.global_visitor)
        # 如果是面向对象语言则长度可能为0
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
                self.func_field2declarator_str[var_info[1]] = node.node_text
        return False


# 在全局范围内搜索函数引用
class GlobalFunctionRefVisitor(ASTVisitor):
    def __init__(self, func_set: Set[str], macro_dict: Dict[str, str] = {}):
        self.func_name_set: Set[str] = func_set
        self.refered_func: Set[str] = set()
        self.macro_dict: Dict[str, str] = macro_dict

    def visit_identifier(self, node: ASTNode):
        identifier: str = node.node_text
        # 引用了函数名或者通过宏定义引用函数名
        # 引用了函数名或者通过宏定义引用函数名
        func_name = identifier
        flag = identifier in self.func_name_set

        if not flag and identifier in self.macro_dict:
            func_name = self.macro_dict[identifier].strip()
            flag = func_name in self.func_name_set

        if flag:
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