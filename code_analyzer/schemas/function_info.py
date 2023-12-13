from typing import List, Tuple, Dict, Set
from code_analyzer.schemas.ast_node import ASTNode

class FuncInfo:
    def __init__(self, parameter_types: List[Tuple[str, str]],
                 name_2_declarator_text: Dict[str, str],
                 declarator_texts: List[str],
                 var_arg: bool,
                 raw_declarator_text: str, func_body: ASTNode, file: str,
                 func_name: str):
        self.parameter_types: List[Tuple[str, str]] = parameter_types
        self.var_arg: bool = var_arg
        self.name_2_declarator_text: Dict[str, str] = name_2_declarator_text
        self.declarator_texts: List[str] = declarator_texts

        # 可变参数
        if len(self.parameter_types) > 0 and self.parameter_types[-1][0] == "va_list":
            self.parameter_types.pop()
            self.var_arg = True
        self.raw_declarator_text: str = raw_declarator_text
        self.func_body: ASTNode = func_body
        self.file: str = file # 相对project根目录的相对路径
        self.func_name: str = func_name


    def set_local_var_info(self, local_var: Dict[str, str]):
        self.local_var: Dict[str, str] = local_var

    # 如果局部变量包含函数指针，将函数指针变量映射到参数类型
    def set_func_var2param_types(self, func_var2param_types: Dict[str, List[str]]):
        self.func_var2param_types: Dict[str, List[str]] = func_var2param_types

    # 如果形参包含函数指针，将函数指针变量映射到参数类型
    def set_func_param2param_types(self, func_param2param_types: Dict[str, List[str]]):
        self.func_param2param_types: Dict[str, List[str]] = func_param2param_types

    # 如果包含支持函数指针的param或者local var
    def set_var_arg_func_param(self, var_arg_func_param: Set[str]):
        self.var_arg_func_param: Set[str] = var_arg_func_param

    def set_var_arg_func_var(self, var_arg_func_var: Set[str]):
        self.var_arg_func_var: Set[str] = var_arg_func_var

    def set_local_var2declarator(self, local_var2declarator: Dict[str, str]):
        self.local_var2declarator: Dict[str, str] = local_var2declarator