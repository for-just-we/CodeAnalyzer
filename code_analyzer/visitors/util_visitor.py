from code_analyzer.visitors.base_visitor import ASTVisitor
from code_analyzer.schemas.ast_node import ASTNode

class IdentifierExtractor(ASTVisitor):
    def __init__(self):
        self.var_name: str = ""
        self.suffix: str = ""
        self.is_function_type: bool = False
        self.is_function: bool = False

    def visit_pointer_declarator(self, node: ASTNode):
        self.suffix += "*"
        return True

    def visit_array_declarator(self, node: ASTNode):
        self.suffix += "*"
        return True

    def visit_identifier(self, node: ASTNode):
        if self.var_name == "":
            self.var_name = node.node_text
        return False

    def visit_function_declarator(self, node: ASTNode):
        # 如果是int (*add)() 则为函数指针变量
        if node.children[0].node_type == "parenthesized_declarator":
            self.is_function_type = True
        # 不然就是函数声明
        else:
            self.is_function = True
        return True

    def visit_parameter_list(self, node: ASTNode):
        return False

class FuncNameExtractor(ASTVisitor):
    def __init__(self):
        self.identifier: str = None
        self.key_node: ASTNode = None

    def visit_identifier(self, node: ASTNode):
        self.identifier = node.node_text
        self.key_node = node

    def visit_type_identifier(self, node: ASTNode):
        self.identifier = node.node_text
        self.key_node = node

    def visit_sized_type_specifier(self, node: ASTNode):
        self.identifier = node.node_text
        self.key_node = node
        return False

# 这里不考虑引用：int& a，引用对应的表达式类型是reference_declarator
class DeclaratorExtractor(ASTVisitor):
    def __init__(self, find_var_name: bool=True):
        self.key_node: ASTNode = None
        self.suffix: str = ""
        # 为True表示寻找变量名identifier、为False表示寻找类型名type_identifier
        self.find_var_name: bool = find_var_name

    def visit_pointer_declarator(self, node: ASTNode):
        self.suffix += "*"
        return True

    def visit_array_declarator(self, node: ASTNode):
        self.suffix += "*"
        return True

    def visit_abstract_pointer_declarator(self, node: ASTNode):
        self.suffix += "*"
        self.key_node = node
        return True

    def visit_identifier(self, node: ASTNode):
        if self.find_var_name:
            self.key_node = node
        return False

    def visit_function_declarator(self, node: ASTNode):
        self.key_node = node
        return False

    def visit_type_identifier(self, node: ASTNode):
        if not self.find_var_name:
            self.key_node = node
        return False

    def visit_sized_type_specifier(self, node: ASTNode):
        if not self.find_var_name:
            self.key_node = node
        return False

    def visit(self, node: ASTNode):
        if node.parent.node_type == "array_declarator" and \
            node != node.parent.children[0]:
            return False
        return True

# 识别结构体定义中field的名称和类型名
class FieldIdentifierExtractor(IdentifierExtractor):
    def __init__(self):
        super().__init__()

    def visit_identifier(self, node: ASTNode):
        return False

    def visit_field_identifier(self, node: ASTNode):
        self.var_name = node.node_text
        return False

class CastTypeDescriptorVisitor(ASTVisitor):
    def __init__(self):
        self.type_name: str = ""
        self.pointer_level: int = 0

    def visit_type_identifier(self, node: ASTNode):
        self.type_name = node.node_text
        return False

    def visit_sized_type_specifier(self, node: ASTNode):
        self.type_name = node.node_text
        return False

    def visit_abstract_pointer_declarator(self, node: ASTNode):
        self.pointer_level += 1
        return True