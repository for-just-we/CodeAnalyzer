
# prompt大模型分析一个target function和indirect-call的summary并判定它们是否匹配
System_Match = """You're a code analyzer tasked with assessing whether an indirect call potentially invoke a target function, given relative information."""

User_Func_Pointer = """## 1.2.summary of the function pointer declaration for the indirect-call:
{}"""

User_Func_Addr = """## 2.2.summary of the target function's address-taken site:
{}"""

User_Match = """The indirect-call expression is: {icall_expr}.

The subsequent text provides the summary of the indirect-call and the corresponding function:

## 1.summary of indirect-call:

## 1.1.summary of the function containing indirect-call and summary of indirect-call itself:
{icall_summary}

{icall_additional}

## 2.summary of target function {func_name}:

## 2.1.summary of the target function:
{func_summary}

{target_additional_information}

Assess if the indirect call {icall_expr} potentially invoke {func_name} based solely on their respective functionalities. Please disregard additional context like detailed implementation or control- & data-flow for now; we'll verify that separately."""
