
summarizing_prompt = """If the following text provides a positive response, answer with only 'yes'; else if it provides a negative response, answer with only 'no'.

{}
"""

# WizardCoder prompt参考 https://github.com/nlpxucan/WizardLM#hiring
wizardcoder_prompt = "Below is an instruction that describes a task. Write a response that appropriately completes the request.\n\n### Instruction:\n{instruction}\n\n### Response:"

wizardcoder_cot_extra = " Let's think step by step."

