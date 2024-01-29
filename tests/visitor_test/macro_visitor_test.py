from code_analyzer.config import parser
from code_analyzer.visitors.func_visitor import FunctionDefVisitor, LocalVarVisitor
from code_analyzer.visitors.global_visitor import GlobalVisitor
from code_analyzer.visitors.macro_visitor import MacroCallExpandVisitor, ICallVisitor

from tree_sitter import Tree
from code_analyzer.schemas.ast_node import ASTNode
from code_analyzer.schemas.function_info import FuncInfo

from typing import Dict, Tuple, List, Set, DefaultDict
from code_analyzer.definition_collector import BaseInfoCollector
from code_analyzer.preprocessor.node_processor import processor, NodeProcessor
from code_analyzer.macro_expand import MacroCallExpandUtil

new_processor = NodeProcessor(unwanted_node_type=set())
file = "../testcases/macro_expand/macro_test.c"
file1 = "../testcases/macro_expand/macro_test1.c"
file2 = "../testcases/macro_expand/macro_test2.c"
file3 = "../testcases/macro_expand/macro_test3.c"
file4 = "../testcases/macro_expand/macro_test4.c"
file5 = "../testcases/macro_expand/macro_test5.c"
file6 = "../testcases/macro_expand/macro_test6.c"
file7 = "../testcases/macro_expand/macro_test7.c"
file8 = "../testcases/macro_expand/macro_test8.c"
file9 = "../testcases/macro_expand/macro_test9.c"
file10 = "../testcases/macro_expand/macro_test10.c"
file11 = "../testcases/macro_expand/macro_test11.c"
file12 = "../testcases/macro_expand/macro_test12.c"
file13 = "../testcases/macro_expand/macro_test13.c"
file14 = "../testcases/macro_expand/macro_test14.c"
file15 = "../testcases/macro_expand/macro_test15.c"
file16 = "../testcases/macro_expand/macro_test16.c"
file17 = "../testcases/macro_expand/macro_test17.c"
file18 = "../testcases/macro_expand/macro_test18.c"
file19 = "../testcases/macro_expand/macro_test19.c"


call_expr_idx = {
    file: 2,
    file1: 3,
    file2: 0,
    file3: 1,
    file4: 1,
    file5: 5,
    file6: 3,
    file7: 2,
    file8: 4,
    file9: 0,
    file10: 0,
    file11: 3,
    file12: 0,
    file13: 0,
    file14: 0,
    file15: 1,
    file16: 2,
    file17: 1,
    file18: 0,
    file19: 0
}

def main():
    cur_file = file13
    global_visitor = GlobalVisitor()
    func_visitor = FunctionDefVisitor()
    code = open(cur_file, 'rb').read()
    tree: Tree = parser.parse(code)
    root_node: ASTNode = processor.visit(tree.root_node)
    global_visitor.traverse_node(root_node)
    func_visitor.traverse_node(root_node)

    func_info_dict: Dict[str, FuncInfo] = func_visitor.func_info_dict
    func_key_2_declarator: Dict[str, str] = dict()
    func_key = list(func_info_dict.keys())[0]
    func_info = list(func_info_dict.values())[0]

    func_key_2_declarator[func_key] = func_info.raw_declarator_text
    local_var_visitor = LocalVarVisitor(global_visitor)
    local_var_visitor.traverse_node(func_info.func_body)

    expand_util = MacroCallExpandUtil(global_visitor.macro_func_bodies, global_visitor.macro_func_args,
                                      global_visitor.var_arg_macro_funcs)
    call_expr: ASTNode = func_info.func_body.children[call_expr_idx[cur_file]].children[0]
    code_text = expand_util.expand_macro_call(call_expr)


    macro_local_var_visitor = LocalVarVisitor(global_visitor)
    expand_call_tree: Tree = parser.parse(code_text.encode("utf-8"))
    expand_root_node: ASTNode = processor.visit(expand_call_tree.root_node)
    macro_local_var_visitor.traverse_node(expand_root_node)

    args: Set[str] = set(func_info.name_2_declarator_text.keys())
    global_vars: Set[str] = set(global_visitor.global_var_2_declarator_text.keys())
    local_vars: Set[str] = local_var_visitor.local_var_2_declarator_text.keys() | \
                           macro_local_var_visitor.local_var_2_declarator_text.keys()
    icall_visitor = ICallVisitor(global_vars, local_vars, args)
    icall_visitor.traverse_node(expand_root_node)
    pass



if __name__ == '__main__':
    main()