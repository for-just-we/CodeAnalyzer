from typing import List, Tuple, Dict
from tree_sitter import Node

class FuncInfo:
    def __init__(self, parameter_types: List[Tuple[str, str]],
                 name_2_declarator_text: Dict[str, str],
                 var_arg: bool,
                 raw_declarator_text: str, func_body: Node, file: str,
                 func_name: str):
        self.parameter_types: List[Tuple[str, str]] = parameter_types
        self.var_arg: bool = var_arg
        self.name_2_declarator_text: Dict[str, str] = name_2_declarator_text

        # 可变参数
        if len(self.parameter_types) > 0 and self.parameter_types[-1][0] == "va_list":
            self.parameter_types.pop()
            self.var_arg = True
        self.raw_declarator_text: str = raw_declarator_text
        self.func_body: Node = func_body
        self.file: str = file # 相对project根目录的相对路径
        self.func_name: str = func_name

    def set_local_var_info(self, local_var: Dict[str, str]):
        self.local_var: Dict[str, str] = local_var