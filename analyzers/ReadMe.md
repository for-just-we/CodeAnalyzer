

# 1.静态分析的问题

## 1.1.由于宏的存在出现代码解析错误

由于宏 `PJ_DEF_DATA` 的存在导致没有正确分析出 `pj_pool_factory_default_policy` 的类型，出现解析错误，3个address-taken function没有被正确confine。

```cpp
PJ_DEF_DATA(pj_pool_factory_policy) pj_pool_factory_default_policy =
{
    &default_block_alloc,
    &default_block_free,
    &default_pool_callback,
    0
};
```

## 1.2.由于存在同名类型导致类型分析错误

```cpp
typedef arith_entropy_decoder *arith_entropy_ptr;
typedef arith_entropy_decoder *arith_entropy_ptr;
```

在分析函数指针的confinement的时候，上述同名类型 `arith_entropy_ptr` 会将函数指针赋值给错误的struct的field，导致潜在漏报。


可能引入漏报的场景不止上面两种，在我们的baseline结果中，2lta的结果往往混入一部分flta，因为有时候2lta由于类型分析错误导致分析结果为空，这时候我们认为2lta出现了type escape，退而采用flta的结果。


# 2.静态分析的实现：

## 2.1.FLTA


# 2.2.MLTA

在实现MLTA时，我们采用2lta实现

2lta的假设：

- (1) the only allowed operation on a function pointer is assignment
  
- (2) there exists no data pointer to a function pointer.


为什么选用2lta，因为没有编译选项的前提下在全程序上分析，尤其是分析潜在escaping type的时候很有可能有遗漏，而且根据mlta的结果，2lta已经相比flta降低了很多误报。因此，决定采用2lta。

| project | baseline | flta | 2lta | 3lta | 4lta | 5lta |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| linux kernel | 180K | 134 | 9.12 | 8.03 | 7.91 | 7.78 |
| Free BSD | 8.7K | 25.5 | 25.5 | 3.53 | 3.50 | 3.49 | 3.49 |
| Firefox | 58K | 115 | 1.86 | 1.84 | 1.82 | 1.82 |

mlta对escape type的定义包括（首先是composite type）：

- unsupported type: 

    * (1) 诸如非复合类型的指针类型 (`char *`)以及整数类型。

    * (2) 其对象指针参与过算数运算的指针类型（不包括访问struct类型的field）。

- escape type:

    * (1) 该类型的一个对象由unsupproted type对象cast而来。
    
    * (2) 对象被 `store` 到unspported type的内存区域。

    * (3) 被cast到unpported type。

不过在我们的benchmark下，这些影响本身不大，我们发现实验的时候没有escape分析几乎没有额外漏报。不过我们发现一个场景可能引起漏报。
我们在[mlta](https://github.com/umnsec/mlta)的[issue](https://github.com/umnsec/mlta/issues/10)下讨论了这个问题。

```cpp
static void
o_stream_default_set_flush_callback(struct ostream_private *_stream,
				    stream_flush_callback_t *callback,
				    void *context)
{
	if (_stream->parent != NULL)
		o_stream_set_flush_callback(_stream->parent, callback, context);

	_stream->callback = callback;
	_stream->context = context;
}
```

总的来说，这类case的模式在于struct field (`_stream->context`) 通过函数参数进行传值（`context`）。
在大部分场景下，函数指针通常直接作为上游某一函数的参数传入，一直传到函数指针被赋值的参数，且中间没有赋值给其它变量。
属于simple data flow ([Kelp paper](https://www.usenix.org/system/files/sec23winter-prepub-350-cai.pdf)中定义的)。
不过当这个调用链涉及到indirect-call时，那么type confinement时可能漏过部分函数。
因此当function pointer struct field被函数参数赋值时，我们将该field标记为escape。


# 3.静态分析result

| part result | precision | recall | F1 |
| ---- | ---- | ---- | ---- |
| flta-min | 19.2 | 75.4 | 26.4 |
| flta-max | 20.5 | 80.8 | 28.1 |
| 2lta-min | 35.3 | 75.0 | 41.7 |
| 2lta-max | 36.5 | 80.4 | 43.7 |