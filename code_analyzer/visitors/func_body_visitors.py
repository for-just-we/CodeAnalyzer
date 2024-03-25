from tree_sitter import Tree
from code_analyzer.schemas.ast_node import ASTNode
from code_analyzer.config import parser
from code_analyzer.preprocessor.node_processor import processor
from typing import Dict, List, Tuple, Set, DefaultDict

from code_analyzer.visitors.base_visitor import ASTVisitor
from code_analyzer.visitors.util_visitor import CastTypeDescriptorVisitor
from code_analyzer.visitors.macro_visitor import ICallVisitor
from code_analyzer.visitors.base_func_visitor import LocalVarVisitor

from code_analyzer.schemas.function_info import FuncInfo
from code_analyzer.schemas.enums import TypeEnum
from code_analyzer.visit_utils.type_util import parsing_type, get_original_type, \
    get_original_type_with_name
from code_analyzer.definition_collector import BaseInfoCollector
from code_analyzer.macro_expand import MacroCallExpandUtil

# 遍历函数体，收集icallsite的类型信息
# 需要考虑函数嵌套调用的关系
class BaseFunctionBodyVisitor(ASTVisitor):
    def __init__(self, arg_infos: Dict[str, str],
                 arg_declarators: Dict[str, str],
                 local_var_infos: Dict[str, str],
                 local_var2declarator: Dict[str, str],
                 collector: BaseInfoCollector):
        # 保存局部变量信息，var name --> var type
        self.local_var_infos: Dict[str, str] = local_var_infos
        self.local_var2declarator: Dict[str, str] = local_var2declarator
        # 保存参数信息
        self.arg_infos: Dict[str, str] = arg_infos
        self.arg_declarators: Dict[str, str] = arg_declarators

        self.collector: BaseInfoCollector = collector

        # 如果该indirect-call引用了结构体field，保存对应的结构体
        self.icall_2_struct_name: Dict[Tuple[int, int], str] = dict()
        # 如果icall引用了field，保存field对应的名字
        self.icall_2_field_name: Dict[Tuple[int, int], str] = dict()

        # 每一个indirect-call对应的函数指针声明的参数类型
        self.icall_2_decl_param_types: Dict[Tuple[int, int], List[str]] = dict()
        # 每一个indirect-call对应的函数指针变量声明的文本
        self.icall_2_decl_text: Dict[Tuple[int, int], str] = dict()

        # 支持可变参数的indirect-call
        self.var_arg_icalls: Set[Tuple[int, int]] = set()


    def set_func_var2param_types(self, func_var2param_types: Dict[str, List[str]]):
        self.func_var2param_types: Dict[str, List[str]] = func_var2param_types

    def set_func_param2param_types(self, func_param2param_types: Dict[str, List[str]]):
        self.func_param2param_types: Dict[str, List[str]] = func_param2param_types

    def set_var_arg_func_param(self, var_arg_func_param: Set[str]):
        self.var_arg_func_param: Set[str] = var_arg_func_param

    def set_var_arg_func_var(self, var_arg_func_var: Set[str]):
        self.var_arg_func_var: Set[str] = var_arg_func_var

    # 处理函数调用的实参数，返回实际参数的base type和pointer level，
    # 如果base type = char*, pointer level = 1 , final type = char**
    # 如果base type = char*, pointer level = -1, final type = char
    def process_argument(self, node: ASTNode, pointer_level: int, icall_loc:
                Tuple[int, int] = None) -> Tuple[str, int, str, str, str]:
        # 1: base_type name, 2: pointer level, 3: declarator, 4: base struct type (only used for function pointer) 5.field_name
        if node.node_type == "identifier":
            def get_base_type(var_name: str, source_dict: Dict[str, str],
                              param_types_dict: Dict[str, List[str]] = None,
                              var_arg_func_vars: Set[str] = None,
                              func_var2declarator: Dict[str, str] = None) -> Tuple[str, str]:
                base_type: str = source_dict.get(var_name, TypeEnum.UnknownType.value)
                base_declarator: str = func_var2declarator.get(var_name, "")
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
                    self.icall_2_decl_text[icall_loc] = base_declarator
                return (base_type, base_declarator)

            var_name: str = node.node_text
            # 局部变量
            if var_name in self.local_var_infos.keys():
                func_var2param_types: Dict[str, List[str]] = \
                    getattr(self, "func_var2param_types", None)
                var_arg_func_var: Set[str] = getattr(self, "var_arg_func_var", None)
                base_type_name, base_declarator = get_base_type(var_name, self.local_var_infos, func_var2param_types,
                                               var_arg_func_var,
                                               self.local_var2declarator)
            # 函数形参
            elif var_name in self.arg_infos.keys():
                func_param2param_types: Dict[str, List[str]] = \
                    getattr(self, "func_param2param_types", None)
                var_arg_func_param: Set[str] = getattr(self, "var_arg_func_param", None)
                base_type_name, base_declarator = get_base_type(var_name, self.arg_infos, func_param2param_types,
                                               var_arg_func_param,
                                               self.arg_declarators)
            # 全局变量
            elif var_name in self.collector.global_var_info.keys():
                base_type_name, base_declarator = get_base_type(var_name, self.collector.global_var_info,
                                          self.collector.func_var2param_types,
                                               self.collector.var_arg_func_vars,
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
            if node.child_count != 3:
                return (TypeEnum.UnknownType.value, 0, "", "", "")
            base_type: Tuple[str, int, str, str, str] = self.process_argument(node.children[0], 0, icall_loc)
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
                    self.icall_2_struct_name[icall_loc] = original_src_type
                    self.icall_2_field_name[icall_loc] = field_name

                # 该field是否支持可变参数
                var_arg_fields: Set[str] = self.collector.var_arg_struct_fields.\
                    get(original_src_type, set())
                if field_name in var_arg_fields:
                    self.var_arg_icalls.add(icall_loc)

            f_type = field_type[0]
            if f_type == TypeEnum.FunctionType.value and f_type != field_type_name:
                f_type = field_type_name
            return (f_type, field_type[1] + pointer_level, field_declarator, original_src_type, field_name)

        # 类型转换
        elif node.node_type == "cast_expression":
            # assert node.child_count == 2
            assert hasattr(node, "type_descriptor")
            descriptor_visitor = CastTypeDescriptorVisitor()
            descriptor_visitor.traverse_node(node.type_descriptor)
            src_type: Tuple[str, int] = get_original_type((descriptor_visitor.type_name,
                                                    descriptor_visitor.pointer_level),
                                                   self.collector.type_alias_infos)
            return (src_type[0], src_type[1], "", "", "")
        # 括号表达式
        elif node.node_type == "parenthesized_expression":
            if hasattr(node, "ERROR"):
                return (TypeEnum.UnknownType.value, 0, "", "", "")
            assert node.child_count == 1
            return self.process_argument(node.children[0], pointer_level, icall_loc)

        # 函数调用
        elif node.node_type == "call_expression":
            callee_name = node.children[0].node_text
            arg_num = node.argument_list.child_count

            from code_analyzer.visitors.util_visitor import arg_num_match
            callee_func_infos: List[FuncInfo] = list(filter(lambda func_info: func_info.func_name == callee_name
                                                       and arg_num_match(arg_num, func_info),
                                                       self.collector.func_info_dict.values()))
            return_type_set: Set[Tuple[str, int]] = set()
            for func_info in callee_func_infos:
                src_type = func_info.return_type
                original_src_type, ori_pointer_level = get_original_type(src_type,
                                                     self.collector.type_alias_infos)
                return_type_set.add((original_src_type, ori_pointer_level))

            # 有可能是宏函数，也有可能定义了不同类型的返回值
            if len(return_type_set) != 1:
                # 如果是宏函数
                return (TypeEnum.UnknownType.value, 0, "", "", "")
            else:
                assert len(return_type_set) == 1
                original_src_type, ori_pointer_level = return_type_set.pop()
                return (original_src_type, ori_pointer_level, "", "", "")

        # 其它复杂表达式
        else:
            if node.child_count == 1:
                return self.process_argument(node.children[0], 0, icall_loc)
            else:
                return (TypeEnum.UnknownType.value, 0, "", "", "")



class ICallInfoVisitor(BaseFunctionBodyVisitor):
    def __init__(self, icall_infos: List[Tuple[int, int]],
                 arg_infos: Dict[str, str],
                 arg_declarators: Dict[str, str],
                 local_var_infos: Dict[str, str],
                 local_var2declarator: Dict[str, str],
                 collector: BaseInfoCollector):
        self.icall_infos: List[Tuple[int, int]] = icall_infos
        super().__init__(arg_infos, arg_declarators, local_var_infos,
                         local_var2declarator, collector)
        # 保存参数信息
        self.arg_info_4_callsite: Dict[Tuple[int, int], List[Tuple[str, int]]] = dict()

        # 每一个indirect-call的文本s
        self.icall_nodes: Dict[Tuple[int, int], ASTNode] = dict()

        # 每一个indirect-call对应的函数指针类型声明文本，当函数指针变量声明是不是用函数格式而是提前用typedef定义函数
        # 指针类型时有用
        self.icall_2_decl_type_text: Dict[Tuple[int, int], str] = dict()

        # 每一个indirect-call对应的每个参数的相关declarator
        self.icall_2_arg_declarators: Dict[Tuple[int, int], List[List[str]]] = dict()
        # 每一个indirect-call对应的每个参数的相关文本
        self.icall_2_arg_texts: Dict[Tuple[int, int], List[str]] = dict()
        # 每一个indirect-call对应的文本
        self.icall_2_text: Dict[Tuple[int, int], str] = dict()
        # 每一个icall对应的argument_list文本
        self.icall_2_arg_text: Dict[Tuple[int, int], str] = dict()

        # 保存宏函数
        self.current_macro_funcs: Dict[Tuple[int, int], str] = dict()
        # 宏展开后的代码
        self.expanded_macros: Dict[Tuple[int, int], str] = dict()
        # 宏调用代码
        self.macro_call_exprs: Dict[Tuple[int, int], str] = dict()

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
        call_expr_node: ASTNode = node

        # 为宏函数
        if node.children[0].node_type == "identifier":
            call_expr_str = node.children[0].node_text
            # 如果是宏函数调用并且
            if call_expr_str in self.collector.macro_funcs:
                self.current_macro_funcs[node.start_point] = call_expr_str
                # 如果没有开启对宏函数的支持，跳过
                if not self.collector.enable_analysis_for_macro:
                    return False
                # 展开宏调用
                expand_util = MacroCallExpandUtil(self.collector.macro_func_bodies,
                                                  self.collector.macro_func_args,
                                                  self.collector.global_visitor.var_arg_macro_funcs)
                try:
                    code_text: str = expand_util.expand_macro_call(node)
                except IndexError as e:
                    return False

                self.expanded_macros[node.start_point] = code_text
                self.macro_call_exprs[node.start_point] = node.node_text
                # 获取宏展开后新定义的变量
                macro_local_var_visitor = LocalVarVisitor(self.collector.global_visitor)
                expand_call_tree: Tree = parser.parse(code_text.encode("utf-8"))
                expand_root_node: ASTNode = processor.visit(expand_call_tree.root_node)
                macro_local_var_visitor.traverse_node(expand_root_node)
                self.local_var_infos.update(macro_local_var_visitor.local_var_infos)
                self.local_var2declarator.update(macro_local_var_visitor.local_var_2_declarator_text)

                # 找到宏调用
                args: Set[str] = set(self.arg_declarators.keys())
                global_vars: Set[str] = set(self.collector.global_var_2_declarator_text.keys())
                local_vars: Set[str] = set(self.local_var2declarator.keys())
                icall_visitor = ICallVisitor(global_vars, local_vars, args)
                icall_visitor.traverse_node(expand_root_node)

                # 没有提取到indirect-call
                if icall_visitor.call_expr is None:
                    return False

                call_expr_node = icall_visitor.call_expr
                call_expr_node.start_point = node.start_point
                call_expr_node.end_point = node.end_point

        # 解析函数指针变量的类型
        assert hasattr(call_expr_node, "argument_list")
        self.icall_2_text[call_expr_node.start_point] = call_expr_node.node_text
        self.icall_2_arg_text[call_expr_node.start_point] = call_expr_node.argument_list.node_text
        # 解析callee expression
        type_name, pointer_level, declarator, base_struct_type, field_name = \
            self.process_argument(call_expr_node.children[0], 0, call_expr_node.start_point)
        type_name, pointer_level = parsing_type((type_name, pointer_level))

        potential_func_type_name, flag = self.get_original_func_type(type_name)
        # 当前callee expression一定是函数指针，
        # 但是如果type_name不是function_type说明函数类型被typedef
        if type_name != TypeEnum.FunctionType.value \
                and flag:
            self.icall_2_decl_param_types[call_expr_node.start_point] = \
                    self.collector.func_type2param_types[potential_func_type_name]
            self.icall_2_decl_type_text[call_expr_node.start_point] = self.collector. \
                                func_type2raw_declarator[potential_func_type_name]
            self.icall_2_decl_text[call_expr_node.start_point] = declarator

            # 如果是结构体field，保存对应的结构体名称
            if base_struct_type != "":
                self.icall_2_struct_name[call_expr_node.start_point] = base_struct_type
            if field_name != "":
                self.icall_2_field_name[call_expr_node.start_point] = field_name

        # 解析argument_list
        arg_type_infos, all_arg_decls, all_arg_texts = self.process_argument_list(call_expr_node.argument_list)
        self.icall_2_arg_texts[call_expr_node.start_point] = all_arg_texts
        self.arg_info_4_callsite[call_expr_node.start_point] = arg_type_infos
        self.icall_2_arg_declarators[call_expr_node.start_point] = all_arg_decls
        self.icall_nodes[call_expr_node.start_point] = call_expr_node

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
            type_info: Tuple[str, int, str, str, str] = self.process_argument(node.children[cur_arg_idx], 0)
            decls: List[str] = self.extract_decl_context(node.children[cur_arg_idx])
            arg_text: str = node.children[cur_arg_idx].node_text
            all_arg_texts.append(arg_text)
            all_arg_decls.append(decls)
            arg_type_infos.append((type_info[0], type_info[1]))
            cur_arg_idx += 1
        return arg_type_infos, all_arg_decls, all_arg_texts


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
            base_type: Tuple[str, int, str, str, str] = self.process_argument(node.children[0], 0, None)
            # 如果解不出base的类型，那么返回未知
            if base_type[0] == TypeEnum.UnknownType.value:
                return []
            # 假定src_type一定指向一个结构体类型
            src_type: Tuple[str, int] = parsing_type((base_type[0], base_type[1]))
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


# 这里主要遍历assignment_expression，如果assignment_expression是将一个函数指针赋值给另一个函数指针，那么认为cast
class EscapeTypeVisitor(BaseFunctionBodyVisitor):
    def __init__(self, arg_infos: Dict[str, str],
                 arg_declarators: Dict[str, str],
                 local_var_infos: Dict[str, str],
                 local_var2declarator: Dict[str, str],
                 collector: BaseInfoCollector,
                 escape_types: DefaultDict[str, Set[str]]):
        super().__init__(arg_infos, arg_declarators, local_var_infos,
                         local_var2declarator, collector)

        # key: struct_type, value: escaped struct fields
        self.escape_types: DefaultDict[str, Set[str]] = escape_types
        self.func_names: Set[str] = set([func_info.func_name for
                                         func_info in self.collector.func_info_dict.values()])

    # paper中关于escape type的标准为
    # (1) The type is cast from an unsupported type;
    # (2) Its objects are stored to objects of an unsupported type;
    # (3) It is cast to an unsupported type.
    # 以上都可以用赋值语句来分析
    def visit_assignment_expression(self, node: ASTNode):
        # 如果出现错误，跳过
        if hasattr(node, "ERROR"):
            return False
        assigned_node: ASTNode = node.children[0]
        if hasattr(assigned_node, "ERROR"):
            return False

        type_name, pointer_level, declarator, base_struct_type, field_name = \
            self.process_argument(assigned_node, 0, None)

        field_func_params: List[str] = self.collector.func_struct_fields.\
            get(base_struct_type, {}).get(field_name, [])
        # 如果该field是函数指针，判断=运算符右侧是不是"unsupported type"
        if len(field_func_params) > 0:
            value_node: ASTNode = node.children[2]
            # 如果被赋值表达式是函数参数
            if self.is_unsupported(value_node):
                self.escape_types[base_struct_type].add(field_name)

    def is_unsupported(self, node: ASTNode) -> bool:
        if node.node_type == "identifier" and node.node_text in self.arg_infos.keys():
            return True
        return False