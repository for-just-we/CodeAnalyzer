from llm_analyzer.parse_util import get_json_result
from llm_analyzer.llm_analyzers.base_analyzer import BaseLLMAnalyzer
from llm_analyzer.llm_prompts.llama_prompt import SystemPrompt1, SystemPrompt2, UserPrompt1, UserPrompt2
from typing import List, Dict
from llama.generation import Llama, ChatPrediction, Dialog

# TODO
class LLama2Analyzer(BaseLLMAnalyzer):
    def __init__(self):
        pass

