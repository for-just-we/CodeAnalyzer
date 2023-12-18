

context = """
You are a text analyzer tasked with analyzing the similarity between two declarators.



Given a function pointer declarator and a function declarator, your task is to evaluate whether the parameter types of function pointer can match that of the function in following steps:

- 1.Extract the parameter list separately from both the function pointer declarator and the function declarator.

- 2.Compare each parameter's type individually for a match, ensuring identical names and pointer hierarchies for types to match.

Note that:

- 1.Certain parameter declarations may be wrapped or followed by macros like UNUSED_PARAM or unused, which do not impact the parameter type. For example, UNUSED_PARAM(int var) is identical to int var.

- 2.Types like int, long, size_t could be considered as compatible due to implicit cast.

The function pointer declarator is 

int				(*handler)(struct input_ctx *);

The function declarator is:

static enum window_copy_cmd_action
window_copy_cmd_cancel(__unused struct window_copy_cmd_state *cs)

If function pointer parameters match function parameters, answer 'yes'; otherwise, answer 'no'.
"""