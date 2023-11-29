from code_analyzer.config import parser
from tree_sitter import Tree
from code_analyzer.visitors.global_visitor import GlobalVisitor
from code_analyzer.schemas.ast_node import ASTNode
from code_analyzer.preprocessor.node_processor import processor

def testTypeDecl():
    file = "../testcases/type_def_test.c"
    tree: Tree = parser.parse(open(file, 'rb').read())
    root_node: ASTNode = processor.visit(tree.root_node)
    globalVisitor = GlobalVisitor()
    globalVisitor.traverse_node(root_node)
    pass

if __name__ == '__main__':
    testTypeDecl()