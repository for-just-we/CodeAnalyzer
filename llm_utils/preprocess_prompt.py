from llm_utils.common_prompt import wizardcoder_prompt, wizardcoder_cot_extra
from typing import List

# preprocess prompt refer to: https://github.com/BerriAI/litellm/blob/7b76a7ed258024c152aed20257a8e18fa6a07a90/litellm/llms/prompt_templates/factory.py#L249
def preprocess_prompt(model_type: str, contents: List[str],
                        add_suffix: bool=False) -> str:
    assert len(contents) in {1, 2}
    prompt = "\n\n".join(contents)
    if model_type == "wizardcoder":
        prompt = wizardcoder_prompt.format(instruction=prompt)
        if add_suffix:
            prompt = prompt + wizardcoder_cot_extra
    # refer to https://github.com/BerriAI/litellm/blob/7b76a7ed258024c152aed20257a8e18fa6a07a90/litellm/llms/prompt_templates/factory.py#L135 and https://github.com/THUDM/ChatGLM3/blob/main/PROMPT.md
    elif model_type == "chatglm":
        if len(contents) == 1:
            prompt = "<|user|>{}\n<|assistant|>".format(contents[0])
        else:
            prompt = "<|system|>{}\n<|user|>{}\n<|assistant|>".format(contents[0], contents[1])
    elif model_type == "codellama":
        if len(contents) == 1:
            prompt = "<s>[INST] {} [/INST]</s>".format(contents[0])
        else:
            prompt = "<s>[INST] <<SYS>>\n{}\n<</SYS>>\n [/INST]\n[INST] {} [/INST]</s>".format(contents[0], contents[1])
    # refer to default template: https://github.com/huggingface/transformers/blob/da20209dbc26a6a870a6e7be87faa657b571b7bc/src/transformers/tokenization_utils_base.py#L1601
    # and: https://huggingface.co/docs/transformers/main/chat_templating
    # here, we use the default template with add_generation_prompt=True
    else:
        if len(contents) == 1:
            prompt = f"<|im_start|>user\n{contents[1]}<|im_end|>\n" \
                + "<|im_start|>assistant"
        else:
            prompt = f"<|im_start|>system\n{contents[0]}<|im_end|>\n" \
                + f"<|im_start|>user\n{contents[1]}<|im_end|>\n" \
                + "<|im_start|>assistant"
    return prompt
