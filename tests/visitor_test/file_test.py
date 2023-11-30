from code_analyzer.config import parser
from code_analyzer.visitors.func_visitor import FunctionDefVisitor
from code_analyzer.visitors.global_visitor import GlobalVisitor
from tree_sitter import Tree
from code_analyzer.schemas.ast_node import ASTNode
from code_analyzer.preprocessor.node_processor import processor

file = "../testcases/struct_case1.c"
file2 = "../testcases/func_test2.c"

if __name__ == '__main__':
    global_visitor = GlobalVisitor()
    visitor = FunctionDefVisitor()
    for i, file_name in enumerate([file, file2]):
        code = open(file_name, 'rb').read()
        tree: Tree = parser.parse(code)
        root_node: ASTNode = processor.visit(tree.root_node)
        global_visitor.traverse_node(root_node)
        visitor.traverse_node(root_node)
        pass
    print()