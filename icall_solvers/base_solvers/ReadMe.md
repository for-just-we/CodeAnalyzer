

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


## 2.2.MLTA


### 2.2.1.principle

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


### 2.2.2.exceptional cases

在source code的某些场景下，由于类型解析错误，比如找不到类型，下面来自fwupd的示例找不到 `FuFirmwareClass` 的定义，导致type confine失败。


```cpp
FuFirmwareClass *klass

object_class->finalize = fu_firmware_finalize;
```



## 2.3.Kelp

### 2.3.1.Rule

Kelp中的一些核心定义：

- 1.simple function pointer: 

    * (1).not referenced by other pointers 

    * (2).does not derive its values by dereferencing other pointers

- 2.confined function: refered only by simple function pointer.

- 3.direct value flow: 可直接从LLVM IR追溯的数据流，不涉及 `store`、`load`。

- 4.indirect value flow: `store` 和 `load` 之间的数据流，需要先做指针分析。


Rule (`pt(s, v) = {o|o ∈ O}` 表示指针v在语句s中的取地址变量，这里只关注function。同时假设定义 `p` 的语句为 `s`):

- Func-Site: `p = &func` (assignment expression), `pt(s, p) = pt(s, p) ∪ {func}`

- Copy: `p = q` (q defined at s1, assignment expression), add def-use edge `(s1, q) -> (s, p)`

- Phi: `p = phi(q, r)` (could be conditional_expression), add def-use edge `(s1, q) -> (s, p), (s2, r) -> (s, p)`

- Field: `p = &q->fld`，add def-use edge `(s1, q) -> (s, p)`，relation `p = FLD(q, fld)`


### 2.3.2.simple function pointer case

#### bind9

```cpp
isc_hashmap_find(ring->keys, dns_name_hash(name), tkey_match,
				  name, (void **)&key);

isc_result_t
isc_hashmap_find(const isc_hashmap_t *hashmap, const uint32_t hashval,
		 isc_hashmap_match_fn match, const void *key, void **valuep) {
	...
	hashmap_find(hashmap, hashval, match, key,
					    &(uint32_t){ 0 }, &idx);
	...
}

static hashmap_node_t *
hashmap_find(const isc_hashmap_t *hashmap, const uint32_t hashval,
	     isc_hashmap_match_fn match, const uint8_t *key, uint32_t *pslp,
	     uint8_t *idxp) {
    ...
    match(node->value, key)
}
```


#### cyclonedds

```cpp
static dds_allocator_t dds_allocator_fns = { ddsrt_malloc, ddsrt_realloc, ddsrt_free };

...
// 只在间接调用处引用
void * ret = (dds_allocator_fns.malloc) (size);
```

#### gdbm

数组类型全局变量相关间接调用

```cpp
static setvar_t setvar[3][3] = {
            /*    s     b    i */
  /* s */    {   s2s,  b2s, i2s },
  /* b */    {   s2b,  b2b, i2b },
  /* i */    {   s2i,  b2i, i2i }
};

...
setvar[vp->type][type] (&v, val, vp->flags);
```


#### libssh

```cpp
// addr-taken function ssh_server_kex_termination
ssh_handle_packets_termination(session, SSH_TIMEOUT_USER,
                                        ssh_server_kex_termination,session);
                                        
int ssh_handle_packets_termination(ssh_session session,
                                   int timeout,
                                   ssh_termination_function fct,
                                   void *user) {
    ...
    while(!fct(user)) 
    ...                                  
}
```


#### selinux

```cpp
static int __cil_copy_node_helper(struct cil_tree_node *orig, uint32_t *finished, void *extra_args)
{
    int (*copy_func)(struct cil_db *db, void *data, void **copy, symtab_t *symtab) = NULL;
    ....
    copy_func = ...
    
    rc = (*copy_func)(db, orig->data, &data, symtab);
}
```


#### pjsip

引用全局变量，且全局变量没有被非赋值语句引用

```cpp
// function pointer declaration
static pj_log_func *log_writer = &pj_log_write;

pj_log_set_log_func(&pj_log_write);

PJ_DEF(void) pj_log_set_log_func( pj_log_func *func )
{
    log_writer = func;
}

...
// indirect-call
(*log_writer)(level, log_buffer, len);
```


### 2.3.3.non-simple function pointer

#### igraph

```cpp
// igraph_i_error_handler会被多次赋值
static IGRAPH_THREAD_LOCAL igraph_error_handler_t *igraph_i_error_handler = 0;

igraph_error_handler_t *igraph_set_error_handler(igraph_error_handler_t *new_handler) {
    igraph_error_handler_t *previous_handler = igraph_i_error_handler;
    igraph_i_error_handler = new_handler;
    return previous_handler;
}
```


```cpp
static void * (*gmp_allocate_func) (size_t) = gmp_default_alloc;

// 全局变量被赋值给别的函数指针
void
mp_get_memory_functions (void *(**alloc_func) (size_t),
			 void *(**realloc_func) (void *, size_t, size_t),
			 void (**free_func) (void *, size_t))
{
  if (alloc_func)
    *alloc_func = gmp_allocate_func;

  if (realloc_func)
    *realloc_func = gmp_reallocate_func;

  if (free_func)
    *free_func = gmp_free_func;
}
```


#### lua

```cpp
lua_newstate(l_alloc, NULL);

LUA_API lua_State *lua_newstate (lua_Alloc f, void *ud) {
  ...
  LG *l = cast(LG *, (*f)(ud, NULL, LUA_TTHREAD, sizeof(LG)));
  ...
  // f被赋值给了其它指针
  g->frealloc = f;
}
```


#### postfix

```cpp
void    msg_output(MSG_OUTPUT_FN output_fn)
{
    ...
    msg_output_fn[msg_output_fn_count++] = output_fn;
}

void    msg_vprintf(int level, const char *format, va_list ap) 
{
    ...
    msg_output_fn[i] (level, vstring_str(vp));
}
```


#### selinux

```cpp
static int (*write_f[SYM_NUM]) (hashtab_key_t key, hashtab_datum_t datum,
				void *datap) = {
common_write, class_write, role_write, type_write, user_write,
	    cond_write_bool, sens_write, cat_write,};
	    
	   
static int avrule_decl_write(avrule_decl_t * decl, int num_scope_syms,
			     policydb_t * p, struct policy_file *fp) {
    ...
    hashtab_map(decl->symtab[i].table, write_f[i], &pd)
}

int hashtab_map(hashtab_t h,
		int (*apply) (hashtab_key_t k,
			      hashtab_datum_t d, void *args), void *args) {
	...
	ret = apply(cur->key, cur->datum, args);
}
```


### 2.3.4.source code实现

source code只考虑下面几种confined function case:

- 通过call expression的参数传值，中间没有其它指针赋值（最终indirect-call直接从函数参数加载）。

- 通过全局变量直接调用，全局变量不应在其它函数内部被re-define以及被其它变量引用。

- 直接在当前function scope定义局部变量并直接调用，局部变量没有进一步赋值给其它函数或者全局变量。


# 3.静态分析result

| part result | precision | recall | F1 |
| ---- | ---- | ---- | ---- |
| flta-min | 19.2 | 75.4 | 26.4 |
| flta-max | 20.5 | 80.8 | 28.1 |
| 2lta-min | 35.3 | 75.0 | 41.7 |
| 2lta-max | 36.5 | 80.4 | 43.7 |