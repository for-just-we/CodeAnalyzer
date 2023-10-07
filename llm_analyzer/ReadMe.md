

# 1.prompt构建参考

[openai api使用示例](https://github.com/openai/openai-cookbook/blob/main/examples/How_to_format_inputs_to_ChatGPT_models.ipynb)

## 1.1.prompt技巧

参考[blog](https://lilianweng.github.io/posts/2023-03-15-prompt-engineering/)

- zero-shot: 直接问，可结合Chain-of-Thought(CoT)

- few-shot: 结合部分样本，可结合CoT

- instruction-prompt: 需要instruction model才好使，说白了就是把输出指明在prompt中

## 1.2.agent相关

关于如何基于LLM可参考的project包括[chemcrow](https://github.com/ur-whitelab/chemcrow-public/)，这个project实现了一个LLM agent，agent可以调用外部tool，tool在这个project中为一个类，类似：

```python
from langchain.tools import BaseTool

class Tool(BaseTool):
    def __init__(self):
        pass
    
    def _run(self, query: str):
        # implement the function
        try:
            self.do_something(query)
        except Exception as e:
            print("...")
```

tool接受一个字符串 `query` 作为输入，默认情况下输出json，但是由于LLM并没有输出格式保证，因此tool的输入可能包含错误信息，导致解析出错。

关于使用[robust-mrkl](https://github.com/whitead/robust-mrkl)构建prompt中各部分的顺序可参考[ChatZeroShotAgent.create_prompt](https://github.com/whitead/robust-mrkl/blob/main/rmrkl/agent.py#L24)，依次包括：

- prefix: system role的一部分，比如 `You are an expert chemist and your task is`，参考[prefix_example](https://github.com/ur-whitelab/chemcrow-public/blob/main/chemcrow/agents/prompts.py#L2)

- format_instruction: system role的一部分，指定输出格式，参考[chemcrow_format_example](https://github.com/ur-whitelab/chemcrow-public/blob/main/chemcrow/agents/prompts.py#L7)和[rmrkl_format_instruction](https://github.com/whitead/robust-mrkl/blob/main/rmrkl/prompts.py#L6)

- question_prompt: user role的一部分，指明问题，通过template + user input合成，参考[chemcrow_question_example](https://github.com/ur-whitelab/chemcrow-public/blob/main/chemcrow/agents/prompts.py#L23)和[rmrkl_question_example](https://github.com/whitead/robust-mrkl/blob/main/rmrkl/prompts.py#L6)


此外Chemcrow采用Thought, Action, Action Input的步骤进行思考，并获得输出后继续用LLM验证一遍，获得二次输出。二次prompt参考[chemcrow_rephrase_example](https://github.com/ur-whitelab/chemcrow-public/blob/main/chemcrow/agents/prompts.py#L49)，为：

```
In this exercise you will assume the role of a scientific assistant. Your task is to answer the provided question as best as you can, based on the provided solution draft.
The solution draft follows the format "Thought, Action, Action Input, Observation", where the 'Thought' statements describe a reasoning sequence. The rest of the text is information obtained to complement the reasoning sequence, and it is 100% accurate.
Your task is to write an answer to the question based on the solution draft, and the following guidelines:
The text should have an educative and assistant-like tone, be accurate, follow the same reasoning sequence than the solution draft and explain how any conclusion is reached.
Question: {question}

Solution draft: {agent_ans}

Answer:
```

相当于第一遍打草稿，第二遍正式提出方案。

此外，LLM输出解析部分可以参考[rmrkl](https://github.com/whitead/robust-mrkl/blob/main/rmrkl/output_parser.py#L13)。总之实现自定义输出解析可以继承[AgentOutputParser](https://github.com/langchain-ai/langchain/blob/master/libs/langchain/langchain/agents/agent.py#L302)。

在输出格式方面，[Haonan Li等人](https://arxiv.org/abs/2308.00245)提出了一个策略，让LLM首先用自然语言回答，然后把自然语言的回答总结为json，从而更好的控制输出格式。

# 2.使用的prompt策略

输出控制方面，采用自然语言输出 + 额外prompt指示LLM summarize in json有一定效果


# 3.模块设计

是否使用keyword假如到prompt中


```
Given some partial function declarators, analyzing the function names and parameter declarations. Extract keywords and Determine whether the arguments in callsite can match the parameters in those functions and whether the function name can match the callee_expression of callsite.
ngx_conf_set_sec_slot(ngx_conf_t *cf, ngx_command_t *cmd, void *conf)
ngx_stream_ssl_preread_merge_srv_conf(ngx_conf_t *cf, void *parent, void *child)
ngx_conf_set_str_slot(ngx_conf_t *cf, ngx_command_t *cmd, void *conf)
ngx_str_rbtree_insert_value(ngx_rbtree_node_t *temp,
    ngx_rbtree_node_t *node, ngx_rbtree_node_t *sentinel)
ngx_stream_ssl_static_variable(ngx_stream_session_t *s,
    ngx_stream_variable_value_t *v, uintptr_t data)
```