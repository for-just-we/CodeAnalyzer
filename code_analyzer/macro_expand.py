from code_analyzer.visitors.macro_visitor import MacroCallExpandVisitor, ExpandCodeConcatVisitor, \
    MacroCallsiteCollectVisitor
from code_analyzer.config import parser
from code_analyzer.schemas.ast_node import ASTNode
from code_analyzer.preprocessor.node_processor import NodeProcessor, processor

from tree_sitter import Tree
from typing import List, Dict, Set

class MacroCallExpandUtil:
    def __init__(self, macro_func_bodies: Dict[str, str], macro_func_args: Dict[str, List[str]],
                 var_arg_macro_funcs: Set[str]):
        self.macro_funcs: Set[str] = set(macro_func_bodies.keys())
        self.macro_func_bodies: Dict[str, str] = macro_func_bodies
        self.macro_func_args: Dict[str, List[str]] = macro_func_args
        self.var_arg_macro_funcs: Set[str] = var_arg_macro_funcs
        self.processor = NodeProcessor(unwanted_node_type=set())

        self.expanded_macros: Set[str] = set()

    def expand_macro_call(self, call_expr: ASTNode):
        code_text: str = self.expand_single_macro(call_expr)
        code_text = self.expand_code_text(code_text)
        return code_text

    def expand_single_macro(self, call_expr: ASTNode):
        macro_in_use: str = call_expr.children[0].node_text
        macro_body_text: str = self.macro_func_bodies[macro_in_use]
        macro_arg_list: List[str] = self.macro_func_args[macro_in_use]
        macro_tree: Tree = parser.parse(macro_body_text.encode("utf8"))
        macro_ast: ASTNode = self.processor.visit(macro_tree.root_node)
        args: List[str] = [arg_node.node_text for arg_node in call_expr.argument_list.children
                           if arg_node.node_type not in {'(', ')', ','}]
        macro_call_expand_visitor = MacroCallExpandVisitor(args, macro_arg_list)
        macro_call_expand_visitor.traverse_node(macro_ast)

        expand_visitor = ExpandCodeConcatVisitor()
        expand_visitor.traverse_node(macro_ast)
        code_text: str = expand_visitor.code
        return code_text

    def expand_code_text(self, code_text: str):
        while True:
            tree: Tree = parser.parse(code_text.encode("utf-8"))
            macro_node: ASTNode = self.processor.visit(tree.root_node)
            macro_callsite_visitor = MacroCallsiteCollectVisitor(self.macro_func_args,
                                                                 self.var_arg_macro_funcs,
                                                                 self.expanded_macros)
            macro_callsite_visitor.traverse_node(macro_node)

            if len(macro_callsite_visitor.macro_callsites) == 0:
                break

            for macro_call_node in macro_callsite_visitor.macro_callsites:
                expand_code_text: str = self.expand_single_macro(macro_call_node)
                new_node = ASTNode("identifier", expand_code_text, (0, 0), (0, 0))
                if macro_call_node.parent is not None:
                    child_idx = macro_call_node.parent.children.index(macro_call_node)
                    new_node.parent = macro_call_node.parent
                    macro_call_node.parent.children[child_idx] = new_node
                else:
                    macro_node = new_node

            expand_visitor = ExpandCodeConcatVisitor()
            expand_visitor.traverse_node(macro_node)
            code_text: str = expand_visitor.code

        return code_text