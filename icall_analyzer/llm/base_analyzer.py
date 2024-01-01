import abc

from typing import List, Dict, Tuple

class BaseLLMAnalyzer:
    def __init__(self, model_type: str):
        self.model_type: str = model_type

    @abc.abstractmethod
    def generate_response(self, diaglog: List[Dict[str, str]]) -> str:
        pass

    def generate_diaglog(self, contents: List[str]) -> List[Dict[str, str]]:
        assert len(contents) in {1, 2}
        if len(contents) == 1:
            return [{"role": "user", "content": contents[0]}]
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


