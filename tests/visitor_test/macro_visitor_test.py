from code_analyzer.config import parser
from code_analyzer.visitors.func_visitor import FunctionDefVisitor, LocalVarVisitor
from code_analyzer.visitors.global_visitor import GlobalVisitor
from tree_sitter import Tree
from code_analyzer.schemas.ast_node import ASTNode
from code_analyzer.schemas.function_info import FuncInfo
from code_analyzer.preprocessor.node_processor import processor

from typing import Dict, Tuple, List, Set, DefaultDict
from code_analyzer.definition_collector import BaseInfoCollector

file = "../testcases/macro_test.c"

def main():
    global_visitor = GlobalVisitor()
    func_visitor = FunctionDefVisitor()
    code = open(file, 'rb').read()
    tree: Tree = parser.parse(code)
    root_node: ASTNode = processor.visit(tree.root_node)
    global_visitor.traverse_node(root_node)
    func_visitor.traverse_node(root_node)

    func_info_dict: Dict[str, FuncInfo] = func_visitor.func_info_dict
    icall_dict: DefaultDict[str, List[Tuple[int, int]]] = {"{}:49:3".format(file): [(1, 1)]}
    refered_func_names: Set[str] = {"isclog_error_callback"}
    func_key_2_declarator: Dict[str, str] = dict()
    func_key = list(func_info_dict.keys())[0]
    func_info = list(func_info_dict.values())[0]

    func_key_2_declarator[func_key] = func_info.raw_declarator_text
    local_var_visitor = LocalVarVisitor(global_visitor)
    local_var_visitor.traverse_node(func_info.func_body)

    collector: BaseInfoCollector = BaseInfoCollector(icall_dict, refered_func_names,
                                                     func_info_dict, global_visitor,
                                                     func_key_2_declarator)
    collector.build_all()

    arg_info: Dict[str, str] = {parameter_type[1]: parameter_type[0]
                                for parameter_type in func_info.parameter_types}
    call_expr: ASTNode = func_info.func_body.children[2].children[0]
    pass



if __name__ == '__main__':
    main()