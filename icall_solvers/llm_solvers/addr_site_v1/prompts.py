
# prompt大模型分析一个target function和indirect-call的summary并判定它们是否匹配
System_Match = """You're a code analyzer tasked with assessing whether an indirect call can invoke a target function, given relative information."""

User_Match = """The indirect-call expression is: {icall_expr}.

The subsequent text provides the summary of the indirect-call and the corresponding function:

## summary of indirect-call:

{icall_summary}

{icall_additional}

## summary of target function {func_name}:

{func_summary}

{target_additional_information}

Assess if the indirect call {icall_expr} can invoke {func_name} based solely on their respective functionalities. Please disregard control- and data-flow information for now; we'll verify that separately."""
