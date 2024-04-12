
symbol类型包括：

- EnumConstant

- Struct 

- TypeAlias

- Field

- Variable

- Function

该[tree-sitter commit](https://github.com/tree-sitter/py-tree-sitter/tree/4e2e765c5d8cf946b886bc757aef5cbf907c82b8)添加了visitor机制，我这里直接引用了。


# 1.实现功能

- 1.收集全局信息，包括project下能收集到的函数定义、类型别名、结构体定义信息。

- 2.继续收集全局信息，搜寻global scope下的函数引用

- 3.遍历每个函数，获取每个函数中函数引用处

- 4.针对存在indirect-call的函数，收集该函数下的局部变量定义，对于icall，尝试基于参数类型匹配潜在的callee。

传统静态分析部分参考[code-analyzer](code_analyzer/ReadMe.md)

- 如果要使用openai的API，请先运行`pip install openai`

- 如果要使用google gemini，请运行 `pip install google-generativeai`。

- 如果调用ChatGLM的API，请先运行 `pip install zhipuai`。

- 如果调用通义千问的API，请运行 `pip install dashscope`。






# 2.LLM的部署

该项目目前支持调用[openai](https://platform.openai.com/), [智谱](https://www.zhipuai.cn/), [google gemini](https://ai.google.dev/), [阿里通义系列](https://dashscope.console.aliyun.com/)的API。本地部署的模型尝试过用3种方式部署：

- [huggingface text-generation-inference](https://github.com/huggingface/text-generation-inference)

- [vllm](https://github.com/vllm-project/vllm)

- [sglang](https://github.com/sgl-project/sglang/)

目前以上部署方式都支持openai的api访问server。不过使用时发现了一些问题

- vllm部署时通过openai api访问时不需要添加 `max_tokens` 参数，但是sglang部署时需要手动指定这些 `max` 参数，容易降低效率。

- vllm和sglang部署只需要传递context长度参数 (vllm的 `--max-model-len` 以及sglang的 `--context-length`)，但是text-generation-inference需要指定 `--max-total-tokens`、`--max-input-length`，感觉不是很灵活。

- vllm单gpu部署时效率感觉很高，但是多gpu部署时容易出现[同步错误](https://github.com/vllm-project/vllm/issues/3839)，这个错误貌似到0.4.0还没解决。

这里建议大家通过vllm或者sglang部署，如果用vllm，用 `openai_local` 调用本地模型时可以不传入 `max_tokens` 参数，但是sglang得传入，可以传个大点的比如 `3072`。