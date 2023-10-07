from code_analyzer.config import parser
from code_analyzer.visitors.func_visitor import FunctionDefVisitor, FunctionBodyVisitor
from code_analyzer.visitors.global_visitor import GlobalVisitor
from tree_sitter import Tree, Node

file = "../testcases/struct_case1.c"

if __name__ == '__main__':
    code = open(file, 'rb').read()
    tree: Tree = parser.parse(code)
    visitor = FunctionDefVisitor()
    visitor.walk(tree)
    global_visitor = GlobalVisitor()
    global_visitor.walk(tree)