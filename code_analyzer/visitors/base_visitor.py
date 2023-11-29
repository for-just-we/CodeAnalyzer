"""This module implements the visitor design pattern for Tree-sitter"""
from code_analyzer.schemas.ast_node import ASTNode

class ASTVisitor:
    # 如果不是感兴趣的结点则继续访问子节点
    def visit(self, node: ASTNode):
        """Default handler that captures all nodes not already handled"""
        return True

    # 返回False表示对子节点不感兴趣，为True则继续访问子节点
    # Traversing ----------------------------------------------------------------
    def on_visit(self, node: ASTNode):
        """
        Handles all nodes visted in AST and calls the underlying vistor methods.

        This method is called for all discovered AST nodes first.
        Override this to handle all nodes regardless of the defined visitor methods.

        Returning False stops the traversal of the subtree rooted at the given node.
        """
        visitor_fn = getattr(self, f"visit_{node.node_type}", self.visit)
        return visitor_fn(node)

    # 前序遍历
    def traverse_node(self, node: ASTNode):
        if self.on_visit(node):
            for child in node.children:
                self.traverse_node(child)