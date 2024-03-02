import logging
from typing import Tuple, Dict
from code_analyzer.schemas.enums import TypeEnum

# 处理指针类型，如果不是指针类型，那相当于没处理
# 需要考虑的是unsigned char这种类型由2个token组成
def parsing_type(cur_type: Tuple[str, int]) -> Tuple[str, int]:
    src_type = cur_type[0]
    pointer_level = cur_type[1]
    # 如果是指针类型
    if src_type.endswith("*"):
        res = src_type.split(" ")
        src_type = ' '.join(res[:-1])
        pointer_level += len(res[-1])
    return (src_type, pointer_level)

#  c语言存在下面语法：
#  typedef struct DDS_Security_Serializer *DDS_Security_Serializer;
#  即dst_type和src_type名字一致，但是pointer_level不一样
def get_original_type(src_type: Tuple[str, int], type_alias_infos: Dict[str, str])\
        -> Tuple[str, int]:
    cur_type_name = src_type[0]
    cur_pointer_level = src_type[1]
    previous_names = set()
    while cur_type_name in type_alias_infos.keys():
        # 出现环路，返回unknown
        if cur_type_name in previous_names:
            return (TypeEnum.UnknownType.value, 0)
        previous_type_name = cur_type_name
        previous_names.add(previous_type_name)
        cur_type_name = type_alias_infos.get(cur_type_name)
        # 处理指针类型
        cur_type_name, cur_pointer_level = parsing_type((cur_type_name, cur_pointer_level))
        if cur_type_name == previous_type_name:
            break
    return (cur_type_name, cur_pointer_level)

def get_original_type_with_name(src_type_name: str, type_alias_infos: Dict[str, str])\
    -> Tuple[str, int]:
    if src_type_name.endswith("*"):
        res = src_type_name.split(" ")
        cur_type_name = " ".join(res[:-1])
        cur_pointer_level = len(res[-1])
    else:
        cur_type_name = src_type_name
        cur_pointer_level = 0
    return get_original_type((cur_type_name, cur_pointer_level), type_alias_infos)