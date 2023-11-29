from code_analyzer.config import parser
from code_analyzer.visitors.func_visitor import FunctionDefVisitor
from code_analyzer.visitors.global_visitor import GlobalVisitor
from tree_sitter import Tree
from code_analyzer.schemas.ast_node import ASTNode
from code_analyzer.preprocessor.node_processor import processor

file = "../testcases/struct_case1.c"

if __name__ == '__main__':
    code = open(file, 'rb').read()
    tree: Tree = parser.parse(code)
    root_node: ASTNode = processor.visit(tree.root_node)
    visitor = FunctionDefVisitor()
    visitor.walk(tree)
    global_visitor = GlobalVisitor()
    global_visitor.walk(tree)