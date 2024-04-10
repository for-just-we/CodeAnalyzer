
summarizing_prompt = """If the following text provides a positive response, answer with only 'yes'; else if it provides a negative response, answer with only 'no'.

{}
"""

qwen_1_5_template = """The text below answer whether an indirect call can invoke a target function; summarize and answer with just 'yes' or 'no'.
    
{}
"""

qwen_1_5_template_type = """The text below answer whether argument types of an indirect call match parameters of a function; summarize and answer with just 'yes' or 'no'.

{}
"""

summarizing_prompt_4_model = {
    "Qwen1.5-14B-Chat": qwen_1_5_template,
    "Qwen1.5-32B-Chat": qwen_1_5_template,
    "Qwen1.5-72B-Chat": qwen_1_5_template
}

summarizing_prompt_4_model_type = {
    "Qwen1.5-14B-Chat": qwen_1_5_template_type,
    "Qwen1.5-32B-Chat": qwen_1_5_template_type,
    "Qwen1.5-72B-Chat": qwen_1_5_template_type
}

# WizardCoder prompt参考 https://github.com/nlpxucan/WizardLM#hiring
wizardcoder_prompt = "Below is an instruction that describes a task. Write a response that appropriately completes the request.\n\n### Instruction:\n{instruction}\n\n### Response:"

wizardcoder_cot_extra = " Let's think step by step."

