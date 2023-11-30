from code_analyzer.schemas.ast_node import ASTNode
from typing import Tuple, List, Dict, Set

from code_analyzer.schemas.enums import TypeEnum
from code_analyzer.visitors.util_visitor import IdentifierExtractor, FieldIdentifierExtractor

# 解析param decl出现错误
class DeclareTypeException(Exception):
    pass

# 在形参定义中以及类型定义中用到，因此&是引用不是取地址运算
def process_declarator(declarator: ASTNode, find_var_name: bool=True) -> Tuple[str, str, ASTNode]:
    from code_analyzer.visitors.util_visitor import DeclaratorExtractor
    extractor = DeclaratorExtractor(find_var_name)
    extractor.traverse_node(declarator)
    if extractor.key_node is None:
        raise DeclareTypeException("Exception happen when processing declarator: {}".format(declarator.node_text))
    return extractor.suffix, extractor.key_node.node_text, extractor.key_node


# 处理一个declaration语句定义了多个变量的情况
# 第二个参数表明是否是在处理struct/union field定义
def process_multi_var_declaration(node: ASTNode, is_field_decl: bool = False,
                                  global_visitor = None)\
        -> Tuple[List[Tuple[str, str]], Dict[str, List[str]], Set[str]]:
    var_list: List[Tuple[str, str]] = list() # 定义的变量类型以及名称
    unknown_var_type_list: List[Tuple[str, str]] = list() # 未知变量名以及prefix
    # 当前处理的变量
    cur_var_decl_idx = 1
    # 将函数指针变量映射到对应的参数类型
    varname2param_types: Dict[str, List[str]] = dict()
    # 函数指针变量中支持可变参数
    var_param_func_vars: Set[str] = set()

    cls = FieldIdentifierExtractor if is_field_decl else IdentifierExtractor

    # 当前处理的依旧是变量定义部分
    while cur_var_decl_idx < node.child_count:
        var_name_extractor = cls()
        var_node: ASTNode = node.children[cur_var_decl_idx]
        # 有初始化参数
        if var_node.node_type == "init_declarator":
            var_name_extractor.traverse_node(var_node.children[0])
        else:
            var_name_extractor.traverse_node(var_node)

        # 是函数声明
        if var_name_extractor.is_function:
            return ()

        # 如果是函数指针变量
        if var_name_extractor.is_function_type:
            from code_analyzer.visitors.func_visitor import extract_param_types
            type_name = TypeEnum.FunctionType.value
            infos = extract_param_types(node)
            param_types: List[str] = infos[0]
            var_arg: bool = infos[1]
            varname2param_types[var_name_extractor.var_name] = param_types
            var_list.append((type_name, var_name_extractor.var_name))
            # 如果支持可变参数
            if var_arg:
                var_param_func_vars.add(var_name_extractor.var_name)
        else:
            unknown_var_type_list.append((var_name_extractor.suffix,
                                          var_name_extractor.var_name))
        cur_var_decl_idx += 1
    type_node: ASTNode = node.children[0]

    if type_node.node_type in {"struct_specifier", "union_specifier"}:
        # 如果声明变量的时候同时出现匿名结构体定义
        if hasattr(type_node, "field_declaration_list"):
            assert global_visitor is not None
            root_type_name, anno_num = global_visitor.process_complex_specifier(type_node,
                                        TypeEnum.StructType.value, global_visitor.anonymous_struct_num)
            global_visitor.anonymous_struct_num = anno_num
            global_visitor.process_struct_specifier(type_node, root_type_name)
        else:
            assert hasattr(type_node, "type_identifier")
            root_type_name = type_node.type_identifier.node_text
        if type_node.node_type == "struct_specifier":
            global_visitor.struct_names.add(root_type_name)
    # 枚举
    elif type_node.node_type == "enum_specifier":
        # 如果声明变量或者field的时候出现匿名枚举的定义
        if hasattr(type_node, "enumerator_list"):
            root_type_name, anno_num = global_visitor.process_complex_specifier(type_node,
                                                                TypeEnum.EnumType.value,
                                                                                global_visitor.anoymous_enum_num)
            global_visitor.anoymous_enum_num = anno_num
        else:
            assert hasattr(type_node, "type_identifier")
            root_type_name = type_node.type_identifier.node_text
        global_visitor.enum_infos.add(root_type_name)
    else:
        root_type_name = type_node.node_text

    for var_info in unknown_var_type_list:
        type_name = root_type_name
        # 指针类型
        if var_info[0] != "":
            type_name += " " + var_info[0]
        var_list.append((type_name, var_info[1]))

    return var_list, varname2param_types, var_param_func_vars
