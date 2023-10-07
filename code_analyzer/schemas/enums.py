from enum import Enum

class TypeEnum(Enum):
    FunctionType = "function_type"
    StructType = "struct_type"
    UnionType = "union_type"
    UnknownType = "unknown_type"
    EnumType = "enum_type"