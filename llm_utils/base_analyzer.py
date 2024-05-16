import abc

from typing import List, Dict

class BaseLLMAnalyzer:
    def __init__(self, model_type: str, temperature: float):
        self.model_type: str = model_type
        self.temperature = temperature

        # 只是用来记录输入和输出的token数
        self.input_token_num: int = 0
        self.output_token_num: int = 0

        # 记录输入和输出的最大token数
        self.max_input_token_num: int = 0
        self.max_output_token_num: int = 0
        self.max_total_token_num: int = 0

    @abc.abstractmethod
    def generate_response(self, diaglog: List[Dict[str, str]]) -> str:
        pass

    def generate_diaglog(self, contents: List[str]) -> List[Dict[str, str]]:
        assert len(contents) in {1, 2}
        if len(contents) == 1:
            return [{"role": "user", "content": contents[0]}]
        else:
            # codegemma chat template refer to https://huggingface.co/google/codegemma-7b-it
            if "codegemma" in self.model_type:
                return [{"role": "user", "content": "\n\n".join(contents)}]
            else:
                return [{"role": "system", "content": contents[0]},
                        {"role": "user", "content": contents[1]}]

    @abc.abstractmethod
    def get_response(self, contents: List[str], add_suffix: bool=False) -> str:
        pass

    @property
    @abc.abstractmethod
    def model_name(self):
        pass


