
PREFIX = """
You are a code analyzer and your task is to analyze whether an indirect-callsite might call some functions, given context of a indirect-call and declarators of functions.
"""

FORMAT_INSTRUCTIONS = """
Conclude previous analysis in json format like {"function1": "yes", "function2": "no"}, If a function can't be reached, mark it as "no" If unsure, label as "uncertain" and if likely reachable, mark as "yes".
The json data should cover results for every function appeared in the function declarators. Respond the json data only.
"""

QUESTION_PROMPT = """
The indirect-call is:
{}

context includes:
{}

potential declarators of called functions include:
{}

You can examine parameter and type names within function declarators, then contrast them with the arguments at the indirect callsite. Additionally, consider the function names within declarators to infer their purpose and evaluate the potential invocation from the callsite.
"""