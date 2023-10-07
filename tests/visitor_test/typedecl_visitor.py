from code_analyzer.config import parser
from tree_sitter import Tree
from code_analyzer.visitors.global_visitor import GlobalVisitor

def testTypeDecl():
    file = "../testcases/type_def_test.c"
    tree: Tree = parser.parse(open(file, 'rb').read())
    globalVisitor = GlobalVisitor()
    globalVisitor.walk(tree)
    pass

if __name__ == '__main__':
    testTypeDecl()