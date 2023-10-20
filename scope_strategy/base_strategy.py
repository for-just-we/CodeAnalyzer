import os

class BaseStrategy:
    def analyze_key(self, callsite_key: str, func_key: str) -> bool:
        callsite_file = callsite_key.split(':')[0]
        func_file = func_key.split(':')[0]
        callsite_path = os.path.dirname(callsite_file)
        func_path = os.path.dirname(func_file)
        return self.analyze(callsite_path, func_path)

    # 基础scope分析策略，如果潜在被调用函数在callsite同级目录或者同级目录子目录下，那么返回true
    def analyze(self, callsite_path: str, func_path: str) -> bool:
        callsite_sub_paths = callsite_path.split('/')
        func_sub_paths = func_path.split('/')
        if len(callsite_sub_paths) > len(func_sub_paths):
            return False
        for i in range(len(callsite_sub_paths)):
            if callsite_sub_paths[i] != func_sub_paths[i]:
                return False
        return True