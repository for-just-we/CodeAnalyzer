
语义匹配部分，目前按以下步骤进行语义匹配：

- 对于indirect-call所在的function，用LLM分析该function的功能，并分析该indirect-call所完成的具体功能。

- 对每个潜在的call target，用LLM分析该call target的功能。

- 分析indirect-call和该call target的功能匹不匹配。