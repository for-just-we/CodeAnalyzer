

# 1.签名匹配

这一步由 `signature_match.ICallSigMatcher` 类完成 存在的Challenge如下：

- 由于特定语法导致解析错误解析不出类型：`void status_prompt_menu_callback(__unused struct menu *menu, u_int idx, key_code key, void *data)`，`__unused` 标识符导致没有正确识别出 `menu` 的类型为 `menu`。

- 由于语法错误导致i-call没有被正确解析

- 原生类型 `uintptr_t` 和 `int`，`long` 的同名问题。

- 如果是动态加载的函数无法直接判断是不是潜在被间接调用的函数，这里暂时不考虑动态加载的函数。

- 有时候 `void*` 指针被隐式强制转化为 `void**` 类型。

```cpp
cairo_list_foreach_entry (cb, struct callback_list, head, link)
cb->func (&surface->base, surface->target, cb->data);
```

`cairo_list_foreach_entry` 是个宏定义，但tree-sitter这里没有成功识别，导致后一句 `cb->func (&surface->base, surface->target, cb->data);` 也没有被正确解析。

出于以上问题，传统类型匹配一定存在误报-漏报trade-off，因此我们在第一步采用一个简单粗暴的匹配策略**最小化漏报**：

- 1.遍历整个project，搜索被引用的函数（被当成变量），暂时不考虑动态加载的函数。

- 2.在被引用的函数中基于参数数量匹配caller和callee。假如icallsite有 `n` 个参数，那么支持可变参数的函数包含的默认参数数量小于等于 `n` 筛选出来，不支持可变参数的函数参数数量刚好为 `n` 的筛选出来。

- 3.上一步筛出来的集合每个函数来进行类型匹配，当前仅当两个参数都是自定义 `struct`, `enum` 等复杂类型的时候进行匹配，匹配成功则挑出来，不成功则不算。对于两个参数有一个以上的类型无法确定或者不是自定义类型（原生类型 `char` 等）直接挑出来，不匹配了。


上述策略会导致相当多的误报，但是可以最小化误报，误报场景包括但不限于：

- 当一个参数是 `struct` 类型，另一个是原生类型 `int`，那么这时只有1个结构体类型，因此匹配函数会直接返回 `true`。因此导致误报。

- 原生类型中的相互转化，比如 `u_char` 可能和 `char` 隐式转化，但是不太可能和 `int` 转化，这里匹配算法依旧会返回 `true`。

上述误报可能基于传统策略进行优化，因此这些难题我们尝试通过LLM优化。

# 2.借助LLM用简单策略过滤一批误报

Challenge

- 一般有的indirect-callsite能够匹配上 n * 100+ 的callee，数量比较大，可能需要分组策略。

- 有的callsite只匹配了几个callee，甚至可能没有误报，也有可能全是误报。

目前策略，采用批处理的方式，一次输入N个callee的信息和1个callsite交给大模型判断，让它过滤最不可能成为callee的一批函数。