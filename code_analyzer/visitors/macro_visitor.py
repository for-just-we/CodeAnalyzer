from code_analyzer.schemas.ast_node import ASTNode
from code_analyzer.visitors.base_visitor import ASTVisitor

from typing import List, Set, Dict

# 将宏函数参数的结点替换成形参
class MacroCallExpandVisitor(ASTVisitor):
    def __init__(self, args: List[str], params: List[str]):
        # 实参文本
        self.args: List[str] = args
        # 形参文本
        self.params: List[str] = params

    def visit_identifier(self, node: ASTNode):
        if node.node_text in self.params:
            idx = self.params.index(node.node_text)
            node.node_text = self.args[idx]


class ExpandCodeConcatVisitor(ASTVisitor):
    def __init__(self):
        self.terminal_nodes: List[ASTNode] = list()

    def visit(self, node: ASTNode):
        if node.child_count == 0:
            self.terminal_nodes.append(node)
            return False
        elif node.node_type == "string_literal":
            self.terminal_nodes.append(node)
            return False
        return super().visit(node)

    @property
    def code(self):
        return " ".join([node.node_text for node in self.terminal_nodes])


class MacroCallsiteCollectVisitor(ASTVisitor):
    def __init__(self, macro_funcs_args: Dict[str, List[str]],
                 var_arg_macro_funcs: Set[str],
                 expanded_macros: Set[str]):
        self.macro_funcs_args: Dict[str, List[str]] = macro_funcs_args
        self.var_arg_macro_funcs: Set[str] = var_arg_macro_funcs
        self.macro_callsites: List[ASTNode] = list()
        self.expanded_macros: Set[str] = expanded_macros

    def visit_call_expression(self, node: ASTNode):
        callee_expr: ASTNode = node.children[0]
        macro: str = callee_expr.node_text
        if callee_expr.node_type == "identifier" and \
            macro in self.macro_funcs_args.keys():
            macro_args_num = len(self.macro_funcs_args[macro])
            args = node.argument_list.children
            args = list(filter(lambda n: n.node_text not in {"(", ")", ","}, args))
            args_num = len(args)
            # 如果不是可变参数宏调用
            if macro_args_num == args_num and macro not in self.var_arg_macro_funcs\
                    and macro not in self.expanded_macros:
                self.macro_callsites.append(node)
                self.expanded_macros.add(macro)
                return False
            # 可变参数宏调用，那么实参 >= 形参
            elif macro in self.var_arg_macro_funcs and args_num >= macro_args_num\
                    and macro not in self.expanded_macros:
                self.macro_callsites.append(node)
                self.expanded_macros.add(macro)
                return False
        return super().visit(node)


class ICallVisitor(ASTVisitor):
    def __init__(self, global_vars: Set[str], local_vars: Set[str],
                 args: Set[str]):
        self.global_vars: Set[str] = global_vars
        self.local_vars: Set[str] = local_vars
        self.args: Set[str] = args
        self.call_expr: ASTNode = None

    def visit(self, node: ASTNode):
        if self.call_expr is not None:
            return False
        else:
            return super().visit(node)

    def visit_call_expression(self, node: ASTNode):
        if self.call_expr is not None:
            return False
        callee_expr: ASTNode = node.children[0]
        # 不是间接调用
        if callee_expr.node_type == "identifier" and \
                callee_expr.node_text not in (self.global_vars | self.local_vars | self.args):
            return super().visit(node)
        # 是间接调用
        else:
            self.call_expr = node
            return False