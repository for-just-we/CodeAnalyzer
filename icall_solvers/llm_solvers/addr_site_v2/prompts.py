
# prompt大模型分析indirect-call所在function的功能并分析该indirect-call所需要实现的功能。
System_func_pointer_Summary = """You are a code summarizer and are provided with declarator-related information of a function pointer. 
Your objective is to succinctly summarize the general intent of the function pointer."""

# prompt大模型分析target function pointer的address-taken site
System_addr_taken_site_Summary = """You're tasked with summarizing the purpose of a function based on its address-taken site."""

# prompt大模型将多个address-taken site的摘要
System_multi_summary = """Your task is to consolidate multiple summaries of address-taken sites for a target function into one concise summary."""

end_multi_summary = """Summarize the purpose of the function {func_name} using provided summaries of each address-taken site."""
