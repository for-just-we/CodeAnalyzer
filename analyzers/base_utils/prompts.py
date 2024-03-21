
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


User_ICall_Summary_Macro = """The expression of the indirect-call is: {icall_expr}

It is located within function {func_name}, whose definition is as follows:

{func_body}

Also, the indirect-call may not be seen util expand macro call {macro_call_expr}, the expanded macro text is: {expanded_macro}

To analyze the functionality of the indirect call {icall_expr}, follow these two steps:

- 1.Summarize the functionality of the {func_name} function to understand its purpose.

- 2.Examine the code surrounding the indirect call {icall_expr} in the expanded macro text and macro call {macro_call_expr} in function {func_name} to determine the specific use of the indirect-call within the context.

You should only response with a concise summary of the indirect call functionality."""

supplement_prompts = {
"user_prompt_match": "If the indirect-call can invoke the target function, answer 'yes'; otherwise, answer 'no'.",
}