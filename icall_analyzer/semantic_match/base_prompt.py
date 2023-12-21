
# prompt大模型分析一个函数的功能并生成summary
System_Func_Summary = """You are a code summarizer tasked with encapsulating the functionality of the {func_name} function in a concise summary."""

User_Func_Summary = """The definition of function {func_name} is as follows, and you should summarize it in one sentence, describing the function's functionality and purpose.

{func_body}"""

# prompt大模型分析indirect-call所在function的功能并分析该indirect-call所需要实现的功能。
System_ICall_Summary = """You are a code analyzer, given an indirect-call and the function it lies in. Your task is to analyze the functionality of the indirect call."""

User_ICall_Summary = """The expression of the indirect-call is: {icall_expr}

It is located within function {func_name}, whose definition is as follows:

{func_body}

To analyze the functionality of the indirect call {icall_expr}, follow these two steps:

- 1.Summarize the functionality of the {func_name} function to understand its purpose.

- 2.Examine the code surrounding the indirect call {icall_expr} and determine its specific use within the context.

You should only response with a concise summary of the indirect call functionality."""

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