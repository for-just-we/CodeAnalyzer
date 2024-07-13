
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
    "Qwen1.5-72B-Chat": qwen_1_5_template,
    "Qwen2-72B-Instruct": qwen_1_5_template,
    "CodeQwen1.5-7B-Chat": qwen_1_5_template,
    "Yi-1.5-34B-Chat": qwen_1_5_template,
    "llama-3-70b-instruct": qwen_1_5_template,
    "llama-3-8b-instruct": qwen_1_5_template,
    "Phi-3-mini-128k-instruct": qwen_1_5_template,
    "Phi-3-medium-128k-instruct'": qwen_1_5_template,
    "codegemma-1.1-7b-it": qwen_1_5_template,
    "Mixtral-8x7B-Instruct-v0.1": qwen_1_5_template,
    "DeepSeek-Coder-V2-Lite-Instruct": qwen_1_5_template,
    "DeepSeek-Coder-V2-Instruct": qwen_1_5_template
}

summarizing_prompt_4_model_type = {
    "Qwen1.5-14B-Chat": qwen_1_5_template_type,
    "Qwen1.5-32B-Chat": qwen_1_5_template_type,
    "Qwen1.5-72B-Chat": qwen_1_5_template_type,
    "Qwen2-72B-Instruct": qwen_1_5_template_type,
    "CodeQwen1.5-7B-Chat": qwen_1_5_template_type,
    "Yi-1.5-34B-Chat": qwen_1_5_template_type,
    "llama-3-70b-instruct": qwen_1_5_template_type,
    "llama-3-8b-instruct": qwen_1_5_template_type,
    "Phi-3-mini-128k-instruct": qwen_1_5_template_type,
    "Phi-3-medium-128k-instruct'": qwen_1_5_template_type,
    "codegemma-1.1-7b-it": qwen_1_5_template_type,
    "Mixtral-8x7B-Instruct-v0.1": qwen_1_5_template_type,
    "DeepSeek-Coder-V2-Lite-Instruct": qwen_1_5_template_type,
    "DeepSeek-Coder-V2-Instruct": qwen_1_5_template_type
}

