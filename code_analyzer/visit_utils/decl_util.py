from tree_sitter import Node
from typing import Tuple, List

from code_analyzer.schemas.enums import TypeEnum
from code_analyzer.visitors.util_visitor import IdentifierExtractor, FieldIdentifierExtractor

# 解析param decl出现错误
class DeclareTypeException(Exception):
    pass

def process_declarator(declarator: Node) -> Tuple[str, str, Node]:
    suffix: str = ""
    while declarator.type not in {"identifier", "function_declarator", "type_identifier"}:
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


def process_declaration(node: Node):
    type_node: Node = node.children[-3]

    if type_node.type == "struct_specifier":
        type_name = type_node.children[1].text.decode('utf8')
    elif type_node.type == "union_specifier":
        type_name = TypeEnum.UnionType.value
    else:
        type_name = type_node.text.decode('utf8')

    var_name_extractor = IdentifierExtractor()
    var_node = node.children[-2]
    # 有初始化参数
    if var_node.type == "init_declarator":
        var_name_extractor.traverse_node(var_node.children[0])
    else:
        var_name_extractor.traverse_node(var_node)

    # 是函数声明
    if var_name_extractor.is_function:
        return None

    # 如果是函数指针变量
    if var_name_extractor.is_function_type:
        type_name = TypeEnum.FunctionType.value

    if not var_name_extractor.is_function_type and var_name_extractor.suffix != "":
        type_name += " " + var_name_extractor.suffix

    return (var_name_extractor.var_name, type_name)

# 处理一个declaration语句定义了多个变量的情况
# 第二个参数表明是否是在处理struct/union field定义
def process_multi_var_declaration(node: Node, is_field_decl: bool = False)\
        -> List[Tuple[str, str]]:
    assert node.children[-1].type == ";"
    var_list: List[Tuple[str, str]] = list() # 定义的变量类型以及名称
    unknown_var_type_list: List[Tuple[str, str]] = list() # 未知变量名以及prefix
    # 当前处理的变量
    cur_var_decl_idx = -2

    cls = FieldIdentifierExtractor if is_field_decl else IdentifierExtractor

    # 当前处理的依旧是变量定义部分
    while abs(cur_var_decl_idx) < node.child_count and \
        node.children[cur_var_decl_idx + 1].type in {",", ";"}:

        var_name_extractor = cls()
        var_node = node.children[cur_var_decl_idx]
        # 有初始化参数
        if var_node.type == "init_declarator":
            var_name_extractor.traverse_node(var_node.children[0])
        else:
            var_name_extractor.traverse_node(var_node)

        # 是函数声明
        if var_name_extractor.is_function:
            return []

        # 如果是函数指针变量
        if var_name_extractor.is_function_type:
            type_name = TypeEnum.FunctionType.value
            var_list.append((type_name, var_name_extractor.var_name))
        else:
            unknown_var_type_list.append((var_name_extractor.suffix,
                                          var_name_extractor.var_name))
        cur_var_decl_idx -= 2
    type_idx = cur_var_decl_idx + 1
    while node.children[type_idx].type in {"storage_class_specifier", "type_qualifier"}:
        type_idx += 1
    type_node: Node = node.children[type_idx]

    if type_node.type == "struct_specifier":
        root_type_name = type_node.children[1].text.decode('utf8')
    elif type_node.type == "union_specifier":
        root_type_name = TypeEnum.UnionType.value
    elif type_node.type == "enum_specifier":
        if type_node.children[1].type == "identifier":
            root_type_name = type_node.children[1].text.decode('utf8')
        # 匿名枚举
        else:
            root_type_name = TypeEnum.EnumType.value
    else:
        root_type_name = type_node.text.decode('utf8')

    for var_info in unknown_var_type_list:
        type_name = root_type_name
        # 指针类型
        if var_info[0] != "":
            type_name += " " + var_info[0]
        var_list.append((type_name, var_info[1]))

    return var_list
