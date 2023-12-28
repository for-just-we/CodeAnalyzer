# prompt大模型分析indirect-call所在function的功能并分析该indirect-call所需要实现的功能。
System_ICall_Summary = """You are a code analyzer, given an indirect-call and the function it lies in. Your task is to analyze the functionality of the indirect call."""

User_ICall_Summary = """The expression of the indirect-call is: {icall_expr}

It is located within function {func_name}, whose definition is as follows:

{func_body}

To analyze the functionality of the indirect call {icall_expr}, follow these two steps:

- 1.Summarize the functionality of the {func_name} function to understand its purpose.

- 2.Examine the code surrounding the indirect call {icall_expr} and determine its specific use within the context.

You should only response with a concise summary of the indirect call. The summary should only describe the purpose or functionality of the indirect-call without additional information."""


# prompt大模型分析一个target function和indirect-call的summary并判定它们是否匹配
System_Match = """You're a code analyzer tasked with assessing whether an indirect call can invoke a target function, given respective contexts."""

# 提供indirect-call text, 相关函数指针或者参数的declarator
# 如果是uncertain type，需要type matcing
# 如果存在type cast，语义分析需要更加仔细点
# Chain-of-thought
# - 1.如果类型比对为uncertain，首先比对类型
# - 2.进行语义分析，首先结合indirect-call的所在的source function以及function pointer declarator，推测indirect-call的功能
# - 3.分析target function的功能，结合indirect-call的功能判断是不是一个caller-callee pair
# Note：
# - 1.只需要结合语义判断是否有可能是一个caller-callee pair，不需要考虑data-flow、control-flow
User_Match = """The indirect-call expression is: {icall_expr}.

It is located within function {src_func_name}, whose definition is as follows:

{source_function_text}

The target function is named: {target_func_name}, with the following definition:

{target_function_text}

Using this information, ascertain whether the indirect-call {icall_expr} can invoke the target function {target_func_name} in following steps:

- 1.Analyze the purpose of indirect-call: Examine the code surrounding the indirect call {icall_expr} and determine its specific use within function {src_func_name}.

- 2.Analyze the functionality of the target function {target_func_name} to understand its purpose.

- 3.Determine whether the indirect-call can invoke the target function based on their functionality. You don't need to consider type match, data-flow, control-flow."""

supplement_prompts = {
"user_prompt_match": "If the indirect-call can invoke the target function, answer 'yes'; otherwise, answer 'no'.",
}