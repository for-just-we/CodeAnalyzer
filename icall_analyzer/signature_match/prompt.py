
system_prompt = """
You task is to determine the potential parent-child relationship between two C struct types."""

user_prompt = """
Given the struct type {struct_type1} and {struct_type2} as reference, assess whether there is parent-child relationship between {struct_type2} and {struct_type1}. Consider the following criteria:

1.Common Initial Fields: verify if the initial fields of both struct types share similar names and types.

2.Type Naming Convention: check whether the struct names {struct_type1} and {struct_type2} reflect a parent-child relationship.

The type definition of {struct_type1} is:

{struct_type1_definition}

The type definition of {struct_type2} is:

{struct_type2_definition}

Answer me whether there is parent-child relationship between struct {struct_type2} and {struct_type1} with "yes" or "no"
"""

system_prompt_declarator = """You are a text analyzer tasked with analyzing the similarity between two declarators.
"""

user_prompt_declarator = """
Given a function pointer declarator and a function declarator, your task is to evaluate whether the parameter types of function pointer can match that of the function in following steps:

- 1.Extract the parameter list separately from both the function pointer declarator and the function declarator.

- 2.Compare the types of each parameter one by one to ensure a match.

Note that:

- 1.Certain parameter declarations may be wrapped or followed by macros like UNUSED_PARAM or unused, which do not impact the parameter type. For example, UNUSED_PARAM(int var) matches the type of int var.

- 2.Types like int, long, size_t could be considered as compatible due to implicit cast.

The function pointer declarator is 

{}

The function declarator is

{}

If function pointer parameters match function parameters, answer 'yes'; otherwise, answer 'no'.
"""

system_prompt_context = """You are a text analyzer tasked with analyzing whether argument types
 are compatible with parameter types of a function parameter."""

user_prompt_context = """
Given an indirect-call, a function declarator. I'm not sure whether their {idx} arguments and parameters types are compatible. 
You need to help me determine.

The indirect-call text is:

{icall_text}

Corresponding argument list is: {arg_text}

The function declarator text is:

{func_decl_text}

{contexts}

Analyze whether the {idx} argument types are compatible with the {idx} parameter types in two steps:

- 1.Extract the expressions of {idx} arguments from argument list and analyze their types with corresponding variable declaration if provided.

- 2.Extract the declarator of {idx} parameters from function declarator text and determine whether types of the parameters match corresponding arguments.

Note that:

- 1.Macros like UNUSED_PARAM could appear in declarations.

- 2.Types like int, long, size_t could be considered as compatible due to implicit cast.

If all {idx} argument types match their respective parameters, respond with 'yes'. Otherwise, or if the information is incomplete, respond with 'no'.
"""

summarizing_prompt = """Summarizing following text with only 'yes', 'no'.

{}
"""