from code_analyzer.schemas.ast_node import ASTNode
from typing import DefaultDict, List, Dict, Set, Tuple


def is_addr_taken_site(node: ASTNode) -> bool:
    # 通过赋值语句传播
    cur_node: ASTNode = node
    while cur_node is not None:
        parent_node: ASTNode = cur_node.parent
        if parent_node is None:
            return False
        # 通过赋值语句传播
        if parent_node.node_type in {"init_declarator", "assignment_expression", "initializer_pair"}:
            if hasattr(parent_node, "="):
                assign_node: ASTNode = getattr(parent_node, "=")
                assign_idx: int = parent_node.children.index(assign_node)
                if parent_node.children.index(cur_node) > assign_idx:
                    return True
                else:
                    return False
            else:
                return False

        # 通过函数参数传播
        elif parent_node.node_type == "argument_list":
            return True

        # 出现了三目表达式
        elif parent_node.node_type == "conditional_expression":
            return True

        cur_node = parent_node

    return False


def get_top_level_expr(node: ASTNode) -> ASTNode:
    node_types: Set[str] = {"compound_statement", "function_definition",
                            "translation_unit", "if_statement",
                            "for_statement", "while_statement",
                            "do_statement", "switch_statement",
                            "preproc_ifdef", "preproc_if", "preproc_else", "preproc_elif"}

    cur_node = node
    while cur_node.parent is not None and \
            cur_node.parent.node_type not in node_types:
        cur_node = cur_node.parent
    return cur_node

# 只关注declaration, assignment_expression, call_expression
def get_local_top_level_expr(node: ASTNode) -> Tuple[ASTNode, int]:
    # 通过赋值语句传播
    cur_node: ASTNode = node
    initializer_level: int = 0
    while cur_node is not None:
        if cur_node.node_type == "declaration":
            return (cur_node, initializer_level)
        elif cur_node.node_type == "assignment_expression":
            return (cur_node, initializer_level)
        elif cur_node.node_type == "call_expression":
            return (cur_node, initializer_level)
        # 出现了三目表达式
        elif cur_node.node_type == "conditional_expression" \
                and hasattr(cur_node, "assignment_expression"):
            return (cur_node, initializer_level)

        if cur_node.node_type == "initializer_list":
            initializer_level += 1

        cur_node = cur_node.parent

    return (cur_node, initializer_level)

def extract_addr_site(refer_sites: DefaultDict[str, List[ASTNode]]):
    addr_taken_sites_: Dict[str, List[ASTNode]] = dict()
    for func_name, refer_site in refer_sites.items():
        addr_taken_sites: List[ASTNode] = list(filter(is_addr_taken_site, refer_site))
        if len(addr_taken_sites) == 0:
            continue
        addr_taken_sites_[func_name] = addr_taken_sites

    return addr_taken_sites_