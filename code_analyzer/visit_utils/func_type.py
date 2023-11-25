import logging
from tree_sitter import Node

def get_func_pointer_name(declarator: Node, node: Node):
    if declarator.children[0].type == "parenthesized_declarator":
        idx = 1
        name_node: Node = declarator.children[0].children[idx]
    elif declarator.children[0].type == "type_identifier":
        name_node = declarator.children[0]
    else:
        logging.debug("error parsing function pointer: ", node.start_point, node.end_point,
                      node.text.decode('utf8'))
        return False
    if name_node.type == "ERROR":
        logging.debug("error parsing function pointer: ", node.start_point, node.end_point,
                      node.text.decode('utf8'))
        return False
    # name_node: Node = declarator.children[0].children[1]
    while name_node.type == "pointer_declarator":
        name_node = name_node.children[1]
    # type_identifier表示类型定义，identifier表示函数指针变量声明
    if name_node.type not in {"type_identifier", "identifier"}:
        logging.debug("error parsing function pointer: ", node.start_point, node.end_point,
                      node.text.decode('utf8'))
        return False
    # assert name_node.type == "type_identifier"
    src_type = name_node.text.decode('utf8')
    return src_type