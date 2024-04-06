# prompt大模型分析一个target function和indirect-call的summary并判定它们是否匹配
System_Match = """You're a code analyzer tasked with assessing whether an indirect call potentially invoke a target function, given respective contexts."""

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

Using this information, ascertain whether the indirect-call {icall_expr} potentially invoke the target function {target_func_name} in following steps:

- 1.Analyze the purpose of indirect-call: Examine the code surrounding the indirect call {icall_expr} and determine its specific use within function {src_func_name}.

- 2.Analyze the functionality of the target function {target_func_name} to understand its purpose.

- 3.Determine whether the indirect-call potentially invoke the target function based on their functionality. You don't need to consider type match, data-flow, control-flow."""


User_Match_macro = """The indirect-call expression is: {icall_expr}.

It is located within function {src_func_name}, whose definition is as follows:

{source_function_text}

Where the indirect-call expression can be seen after expand macro call: {macro_call_expr}, the expanded macro text is: {macro_text}.

The target function is named: {target_func_name}, with the following definition:

{target_function_text}

Using this information, ascertain whether the indirect-call {icall_expr} potentially invoke the target function {target_func_name} in following steps:

- 1.Analyze the purpose of indirect-call: Examine the code surrounding the indirect call {icall_expr} and determine its specific use within function {src_func_name}.

- 2.Analyze the functionality of the target function {target_func_name} to understand its purpose.

- 3.Determine whether the indirect-call potentially invoke the target function based on their functionality. You don't need to consider type match, data-flow, control-flow.
"""

supplement_prompts = {
"user_prompt_match": "If the indirect-call potentially invoke the target function, answer 'yes'; otherwise, answer 'no'.",
}