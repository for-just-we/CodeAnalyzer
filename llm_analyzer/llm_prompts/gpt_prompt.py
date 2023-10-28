
SystemPrompt1 = """You are a code analyzer tasked with evaluating the likelihood of an indirect callsite effectively invoking a certain function. 
Your analysis should primarily focus on assessing the semantic similarity between the indirect call, its context, and the function declarator. 
Additionally, consider the correspondence between formal and actual parameter names, as well as the compatibility of type names. 
Your goal is to assess the likelihood of the indirect callsite invoking these function and provide a reasoned prediction.
"""

UserPrompt1 = """Please evaluate the following indirect call:

{}

The context provides information about variables and types, as follows:

{}

Their function declarator is as follows:

{}

Pay special attention to semantic similarity between the indirect call, context, and function declarators, as well as the alignment of parameter names and type compatibility. 
Your analysis should determine if there is a substantial possibility of the indirect call effectively invoking the function. 
Provide your answer with only 'yes' (for likely), or 'no' (for unlikely).
"""


SystemPrompt1_ = """You are a code analyzer tasked with evaluating the likelihood of an indirect callsite effectively invoking a function.
The indirect call is a macro function so you should first analyze the macro of the call expression and determine the true text of indirect call.  
Then your analysis should primarily focus on assessing the semantic similarity between the indirect call, its context, and the function declarators. 
The macro may be a little helpful in assessing the semantic of the indirect call.
Additionally, consider the correspondence between formal and actual parameter names, as well as the compatibility of type names. 
Your goal is to assess the likelihood of the indirect callsite invoking these functions and provide a reasoned prediction.
"""

UserPrompt1_ = """Please evaluate the following indirect call:

{}

The corresponding macro definition is:

{}

The context provides information about variables and types, as follows:

{}

Their function declarators are as follows:

{}

Pay special attention to semantic similarity between the indirect call, context, and function declarators, as well as the alignment of parameter names and type compatibility. 
Your analysis should determine if there is a substantial possibility of the indirect call effectively invoking any of the listed functions. 
Provide your answer with only 'yes' (for likely), or 'no' (for unlikely).
"""

UserPrompt2 = """Summarizing following text with 'yes', 'no'.

{}
"""