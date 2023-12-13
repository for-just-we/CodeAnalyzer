
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

- 3.Note that certain parameter declarations may be wrapped or followed by macros like UNUSED_PARAM or unused, which do not impact the parameter type. Therefore, you should ignore such macros.

The function pointer declarator is 

{}

The function declarator is

{}

If the function pointer can correctly invoke the function, answer 'yes'. Otherwise, answer 'no'.
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

Note that macros like UNUSED_PARAM could appear in declarations.
If all {idx} arguments match {idx} parameters, answer me with only 'yes'. Otherwise, or if you feel the provided information is incomplete. Answer me with only 'no'.
"""

summarizing_prompt = """Summarizing following text with only 'yes', 'no'.

{}
"""