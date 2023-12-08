
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
Given a function pointer declarator and a function declarator, your task is to evaluate whether the function pointer can correctly invoke the function. Consider the following criteria:

1.Parameter Type and Name Matching:
- Verify the correspondence of each parameter's type between the function pointer and the function.
- Some parameter declaration may be wrapped or followed by macro like UNUSED_PARAM or __unused__.
- If the parameter type is challenging to determine, consider assessing the similarity between parameter names.

2.Naming Convention:
- Examine whether the name of the function pointer aligns with the function name.
- Consider similarities in naming conventions to determine the relationship between the function pointer and the function.

The function pointer declarator is 

{}

The function declarator is

{}

Answer the compatibility of the function pointer with the corresponding function with only 'yes' or 'no'.
"""

summarizing_prompt = """Summarizing following text with only 'yes', 'no'.

{}
"""