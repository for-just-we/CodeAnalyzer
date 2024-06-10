from tree_sitter import Node
from typing import Set
from code_analyzer.schemas.ast_node import ASTNode
import os

def get_node_text(node: Node) -> str:
    try:
        text = node.text.decode('utf8')
    except UnicodeDecodeError:
        text = node.text.decode('ISO-8859-1')
    return text

class NodeProcessor:
    def __init__(self, unwanted_node_type: Set[str] = {}, max_depth: int = 500):
        self.unwanted_node_type: Set[str] = unwanted_node_type
        self.max_depth = max_depth
        self.cur_file = ""

    # 处理类型定义
    def visit(self, node: Node, depth: int = 0) -> ASTNode:
        # 递归深度限制
        if depth >= self.max_depth:
            return None
        if node.type in self.unwanted_node_type:
            return None
        ast_node: ASTNode = ASTNode(node.type,
                                    get_node_text(node),
                                    node.start_point, node.end_point,
                                    file=self.cur_file)
        # if node.type == "function_definition":
        #     if node.prev_sibling is not None and node.prev_sibling.type == "comment":
        #         comment = get_node_text(node.prev_sibling)
        #         print(node.type)
        for child in node.children:
            child_type: str = child.type
            if child_type in self.unwanted_node_type:
                continue
            child_node: ASTNode = self.visit(child, depth + 1)
            if child_node is None:
                continue
            child_node.parent = ast_node
            ast_node.children.append(child_node)
            # 如果node已有对应属性
            if hasattr(ast_node, child_type):
                attr = getattr(ast_node, child_type)
                # 如果attr是Node
                if isinstance(attr, ASTNode):
                    setattr(ast_node, child_type, [attr, child_node])
                # 如果attr是List
                else:
                    assert isinstance(attr, list)
                    attr.append(child)
            # 如果node没有对应属性
            else:
                setattr(ast_node, child_type, child_node)
        return ast_node

root_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
f = open(f"{root_path}/resources/filtered_keyword.txt", 'r', encoding='utf-8')
line = f.read()
keywords: set = set(line.split(' '))
keywords.add('\n')
processor = NodeProcessor(keywords)