# prompt大模型分析一个target function和indirect-call的summary并判定它们是否匹配
System_Match = """You're a code analyzer."""

# 提供indirect-call text, 相关函数指针或者参数的declarator
# 如果是uncertain type，需要type matcing
# 如果存在type cast，语义分析需要更加仔细点
# Chain-of-thought
# - 1.如果类型比对为uncertain，首先比对类型
# - 2.进行语义分析，首先结合indirect-call的所在的source function以及function pointer declarator，推测indirect-call的功能
# - 3.分析target function的功能，结合indirect-call的功能判断是不是一个caller-callee pair
# Note：
# - 1.只需要结合语义判断是否有可能是一个caller-callee pair，不需要考虑data-flow、control-flow
User_Match = """You are tasked with assessing whether an indirect call potentially invoke a target function, given respective contexts.
The indirect-call expression is: {icall_expr}.

# 1.context related to indirect-call

## 1.1.source function

It is located within function {src_func_name}, whose definition is as follows:

{source_function_text}

{icall_additional}

# 2.context related to target function

## 2.1.target function definition

The target function is named: {target_func_name}, with the following definition:

{target_function_text}

{target_additional_information}

Assess if {target_func_name} could be one of the target function that indirect call {icall_expr} potentially invoke in following steps: 

- 1.Analyze the purpose of indirect-call:

    * 1.1.Summarize the functionality of the source function {func_name} to understand the function's purpose.
    
    * 1.2.Examine the code in source function surrounding the indirect call `{icall_expr}` and determine the specific use of the indirect call within the context.
    
    * 1.3.If global context is provided, you may summarize the function pointer's purpose with global context provided before.
    
    * 1.4.Understand the purpose of the indirect-call following step 1.1, step 1.2, and step 1.3.
    
- 2.Analyze the functionality of the target function {target_func_name} to understand its purpose.

   * 2.1.Understand the functionality of target function {target_func_name} with text of its function body.
   
   * 2.2.If the code of address-taken sites of target function is provided, understand the purpose of the function pointers it assign to.
   
- 3.Determine whether the indirect-call potentially invoke the target function based on their functionality.

Please disregard additional context like detailed implementation, control- & data-flow, or types and class hierarchy for now; we'll verify that separately."""


User_Match_macro = """The indirect-call expression is: {icall_expr}.

It is located within function {src_func_name}, whose definition is as follows:

{source_function_text}

Where the indirect-call expression can be seen after expand macro call: {macro_call_expr}, the expanded macro text is: {macro_text}.

The target function is named: {target_func_name}, with the following definition:

{target_function_text}

Assess if {target_func_name} could be one of the target function that indirect call {icall_expr} potentially invoke in following steps: 

- 1.Analyze the purpose of indirect-call: Examine the code surrounding the indirect call {icall_expr} and determine its specific use within function {src_func_name}.

- 2.Analyze the functionality of the target function {target_func_name} to understand its purpose.

- 3.Determine whether the indirect-call potentially invoke the target function based on their functionality. You don't need to consider type match, data-flow, control-flow.

Please disregard additional context like detailed implementation, control- & data-flow, or types and class hierarchy for now; we'll verify that separately.
"""

supplement_prompts = {
"user_prompt_match": "If the indirect-call potentially invoke the target function, answer 'yes'; otherwise, answer 'no'.",
}