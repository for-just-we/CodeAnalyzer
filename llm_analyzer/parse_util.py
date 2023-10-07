import json
import logging
import re
from typing import Dict, List

json_pattern = r"\{[^{}]*\}"

def get_json_result(input_string) -> Dict[str, str]:
    json_matches = re.findall(json_pattern, input_string)
    json_datas = {}
    for json_match in json_matches:
        try:
            json_dict = json.loads(json_match)
            for func_name, decision in json_dict.items():
                # 存在重复解析的函数名
                if func_name in json_datas.keys():
                    continue
                # 如果分析结果不是str类型，跳过
                if not isinstance(decision, str):
                    continue
                if decision.lower() in {"yes", "no", "uncertain"}:
                    json_datas[func_name] = decision.lower()
        except json.JSONDecodeError:
            logging.info("json parsing error")
    return json_datas

def batch_dict(dict_to_batch: Dict[str, str], num_per_batch: int) -> List[Dict[str, str]]:
    dict_list = list(dict_to_batch.items())  # 将字典转换为包含键值对元组的列表
    num_items = len(dict_list)  # 字典中的元素数量
    result = []  # 存储结果的列表

    for i in range(0, num_items, num_per_batch):
        batch_items = dict_list[i:i + num_per_batch]  # 获取一个批次的元素
        batch_dict: Dict[str, str] = {key: value for key, value in batch_items}  # 将元素转换回字典
        result.append(batch_dict)  # 将批次添加到结果列表中

    return result