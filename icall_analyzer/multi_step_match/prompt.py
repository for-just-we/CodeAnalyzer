
# prompt大模型分析一个target function和indirect-call的summary并判定它们是否匹配
System_Match = """You're a code analyzer tasked with assessing whether an indirect call can invoke a target function, given their respective summaries."""

User_Match = """The indirect-call expression is: {icall_expr}.

The subsequent text provides the summary of the indirect-call and the corresponding function:

{icall_summary}

The target function is named: {func_name}, with the following summary:

{func_summary}

Using this information, ascertain whether the indirect-call {icall_expr} can invoke the target function {func_name} based on their functionality."""

supplement_prompts = {
"user_prompt_match": "If the indirect-call can invoke the target function, answer 'yes'; otherwise, answer 'no'.",
}