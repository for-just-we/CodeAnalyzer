import logging
from code_analyzer.schemas.ast_node import ASTNode

def get_func_pointer_name(declarator: ASTNode, node: ASTNode):
    if declarator.child_count != 2:
        logging.debug("error parsing function pointer: ", node.start_point, node.end_point,
                      node.node_text)
        return False
    if declarator.children[0].node_type == "parenthesized_declarator":
        from code_analyzer.visitors.util_visitor import FuncNameExtractor
        func_name_extractor = FuncNameExtractor()
        func_name_extractor.traverse_node(declarator.children[0])
        name_node: ASTNode = func_name_extractor.key_node
    elif declarator.children[0].node_type == "type_identifier":
        name_node = declarator.children[0]
    else:
        logging.debug("error parsing function pointer: ", node.start_point, node.end_point,
                      node.node_text)
        return False
    if name_node is None or name_node.node_type == "ERROR":
        logging.debug("error parsing function pointer: ", node.start_point, node.end_point,
                      node.node_text)
        return False
    # name_node: Node = declarator.children[0].children[1]
    while name_node.node_type == "pointer_declarator":
        name_node = name_node.children[1]
    # type_identifier表示类型定义，identifier表示函数指针变量声明
    if name_node.node_type not in {"type_identifier", "identifier"}:
        logging.debug("error parsing function pointer: ", node.start_point, node.end_point,
                      node.node_text)
        return False
    # assert name_node.type == "type_identifier"
    src_type = name_node.node_text
    return src_type