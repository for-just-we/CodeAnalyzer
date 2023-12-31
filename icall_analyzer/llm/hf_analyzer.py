import logging
import time
from typing import List, Tuple
from icall_analyzer.llm.base_analyzer import BaseLLMAnalyzer
from huggingface_hub import InferenceClient

class HuggingFaceAnalyzer(BaseLLMAnalyzer):
    def __init__(self, model_type: str, address: str, temperature: float=0):
        super().__init__(model_type)
        self.address = "http://" + address
        self.temperature = temperature
        self.client = InferenceClient(self.address)

    def get_hf_response(self, prompt: str, times: int) -> Tuple[str, bool, int]:
        """
        prompt: system_prompt + user_prompt
        """
        def handle_error(exception, sleep_time):
            error_message = f"{exception.__class__.__name__} in request, message is: {exception}"
            logging.debug(error_message)
            time.sleep(sleep_time)
            return str(exception), False, times

        try:
            resp_text: str = self.client.text_generation(prompt,
                                                temperature=self.temperature)
            return resp_text, True, times
        # 达到rate limit
        except Exception as e:
            return handle_error(e, 60)

    def get_response(self, contents: List[str]) -> str:
        assert len(contents) in {1, 2}
        prompt = "\n\n".join(contents)
        resp: Tuple[str, bool, int] = self.get_hf_response(prompt, 0)
        # 没有成功解析出来，就最多重试3次
        while not resp[1]:
            if resp[2] >= 3:
                return ""
            resp: Tuple[str, bool, int] = self.get_hf_response(prompt, resp[2])
        content: str = resp[0]
        return content

    def model_name(self):
        return f"{self.model_type}-{self.temperature}"