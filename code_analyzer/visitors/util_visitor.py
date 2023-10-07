from code_analyzer.visitors.tree_sitter_base_visitor import ASTVisitor

from tree_sitter import Node

class IdentifierExtractor(ASTVisitor):
    def __init__(self):
        self.var_name: str = ""
        self.suffix: str = ""
        self.is_function_type: bool = False
        self.is_function: bool = False

    def visit_pointer_declarator(self, node: Node):
        self.suffix += "*"
        return True

    def visit_array_declarator(self, node: Node):
        self.suffix += "*"
        return True

    def visit_identifier(self, node: Node):
        if self.var_name == "":
            self.var_name = node.text.decode('utf8')
        return False

    def visit_function_declarator(self, node: Node):
        # 如果是int (*add)() 则为函数指针变量
        if node.children[0].type == "parenthesized_declarator":
            self.is_function_type = True
        # 不然就是函数声明
        else:
            self.is_function = True
        return True

    def visit_parameter_list(self, node: Node):
        return False

# 识别结构体定义中field的名称和类型名
class FieldIdentifierExtractor(IdentifierExtractor):
    def __init__(self):
        super().__init__()

    def visit_identifier(self, node: Node):
        return False

    def visit_field_identifier(self, node: Node):
        self.var_name = node.text.decode('utf8')
        return False

class CastTypeDescriptorVisitor(ASTVisitor):
    def __init__(self):
        self.type_name: str = ""
        self.pointer_level: int = 0

    def visit_type_identifier(self, node: Node):
        self.type_name = node.text.decode('utf8')
        return False

    def visit_abstract_pointer_declarator(self, node: Node):
        self.pointer_level += 1
        return True