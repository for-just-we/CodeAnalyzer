
# prompt大模型分析一个target function和indirect-call的summary并判定它们是否匹配
System_Match = """You're a code analyzer tasked with assessing whether an indirect call can invoke a target function, given relative information."""

User_Match = """The indirect-call expression is: {icall_expr}.

The subsequent text provides the summary of the indirect-call and the corresponding function:

{icall_summary}

{icall_additional}

The target function is named: {func_name}, with the following summary:

{func_summary}

{target_additional_information}

Using this information, ascertain whether the indirect-call {icall_expr} can invoke the target function {func_name} based on their functionality."""