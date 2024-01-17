
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



