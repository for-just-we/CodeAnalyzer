
# prompt大模型分析indirect-call所在function的功能并分析该indirect-call所需要实现的功能。
System_func_pointer_Summary = """You are a code summarizer and are provided with declarator-related information of a function pointer. 
Your objective is to succinctly summarize the general intent of the function pointer."""

# prompt大模型分析target function pointer的address-taken site
System_addr_taken_site_Summary = """You're tasked with summarizing the purpose of a function based on its address-taken site."""

# prompt大模型将多个address-taken site的摘要
System_multi_summary = """Your task is to consolidate multiple summaries of address-taken sites for a target function into one concise summary."""

end_multi_summary = """Summarize the purpose of the function {func_name} using provided summaries of each address-taken site."""


# prompt大模型分析一个target function和indirect-call的summary并判定它们是否匹配
System_Match = """You're a code analyzer tasked with assessing whether an indirect call potentially invoke a target function, given relative information."""

User_Func_Pointer = """## 1.2.summary of the function pointer declaration for the indirect-call:
{}"""

User_Func_Addr = """## 2.2.summary of the target function's address-taken site:
{}"""

User_ICall_local = """## 1.1.summary of function {parent_func_name} containing indirect-call and summary of indirect-call itself:
{icall_summary}"""

User_Func_Local = """## 2.1.summary of the target function:
{func_summary}"""

User_Match = """The indirect-call expression is: {icall_expr}.

The subsequent text provides the summary of the indirect-call and the corresponding function:

{icall_title}

{icall_summary}

{icall_additional}

{func_title}

{func_summary}

{target_additional_information}

# Question:
Assess if {func_name} could be one of the target function that indirect call {icall_expr} potentially invoke based solely on their respective functionalities. Please disregard additional context like detailed implementation, control- & data-flow, or types and class hierarchy for now; we'll verify that separately."""
