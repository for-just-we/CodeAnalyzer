
运行，code_analyzer基于[tree-sitter](https://github.com/tree-sitter/py-tree-sitter/)实现，使用前需要build一个 `my-languages.so` 或者 `my-languages.dylib` 放在根目录的 `resources` 目录下。

可以直接通过在`<project_root>/resources` 目录下运行 `python build.py` build动态链接库，但是注意需要先下载[tree-sitter-c](https://github.com/tree-sitter/tree-sitter-c)和[tree-sitter-cpp](https://github.com/tree-sitter/tree-sitter-cpp)到 `resources` 目录下

# 1.将tree-sitter AST转化为自定义AST

tree-sitter自定义的AST直接使用起来体验非常不好，tree-sitter的ASTNode不提供通过field访问子节点的方式，tree-sitter的Node类包含 `children`, `children_count` 域。

- `children` 为一个由Node构成的子节点 `list`。

- `child_count` 为子节点数量。

- `type` 为节点类型。

- `text` 为该节点对应的代码文本。

然而，tree-sitter不提供field方式访问子节点，比如 `call_expression` 类Node没有 `callee` 域访问对应的callee表达式，必须通过诸如 `children[0]` 的通过子节点索引方式来访问。 
这在从 `struct piddesc const * const table = piddesc_tables_all[k];` 这样的 `declarator` 中提取变量名 `table` 和类型名 `piddesc*` 的时候非常难受。

因此，我们首先简化AST，我们ASTNode的定义放在[ast_node.py](schemas/ast_node.py)，我们通过[NodeProcessor](preprocessor/node_processor.py)来遍历tree-sitter的node获取简化版AST。
在遍历AST时：

- tree-sitter的默认AST连分隔符 `(`, `)`, `,` 都放在子节点里面。因此我们在[filtered_keyword.txt](../resources/filtered_keyword.txt)中定义了一些关键词，这些关键词对应的ASTNode不会出现在简化版的AST中。
比如，`type_qualifier` 对应了 `const` 等修饰符；然而，我们只是实现一个语法分析工具分析变量名、类型名等。不需要关注是否常量等信息，因此我们在简化AST时过滤了这些信息。

- 新构建的ASTNode除了 `children` 域，我们还增加了通过对应域访问子节点。 
假设有一个 `call_expression`，有2个子节点，类型分别为 `identifier`(callee表达式), `argument_list`(实参列表)。
那么该 `call_expression` 有一个 `identifier` 域指向callee，而 `argument_list` 域指向实参列表。
这么做有点不优雅，因为callee对应的域最好命名为 `callee`，这也方便在callee表达式不是 `identifier` 类型时进行访问。
然而这样做可以极大减少人工制定规则的成本，以后可以考虑优化。

- 有时候一个AST节点可能有多个同类型的子节点，如果是这样，那对应域会变为一个 `list`。
比如 `int a, b;`，其根节点为 `declarator`，子节点包含2个 `identifier`(`a`, `b`)。
那么这个时候 `identifier` 就会变成一个 `List[ASTNode]`，元素为 `a`, `b` 对应的 `ASTNode`。

# 2.遍历AST获取全局信息

这一步主要遍历AST获取(不限于)：

- 结构体、联合体定义信息 (`struct`, `union`)

- 类型别名信息 (`typedef`)

- 函数指针定义信息 (`function_declarator`)

# 3.签名匹配

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

局限性，主要来自宏定义：

- address-taken function的函数名会被赋值给宏名，然后通过宏名进一步进行赋值，这会导致address-taken function的分析出现误报。

# 4.Hard Case

tree-sitter的语法解析不是完美的，在遇到一些case容易生成 `ERROR`。下面列举了一些case导致了类型匹配失败。

## 4.1.bind9

下面代码中 

- `DNS__DB_FLARG` 的存在导致分析形参的时候变量名为 `DNS__DB_FLARG` 而不是 `rdataset`，
进而在分析函数指针 `rdataset->methods->disassociate` 找不到 `rdataset` 对应的类型从而解析不出函数指针声明。

- `DNS__DB_FLARG_PASS` 也导致分析出的参数名是 `DNS__DB_FLARG_PASS` 而不是 `rdataset`。

```cpp
void
dns__rdataset_disassociate(dns_rdataset_t *rdataset DNS__DB_FLARG) {
	...
	if (rdataset->methods->disassociate != NULL) {
		(rdataset->methods->disassociate)(rdataset DNS__DB_FLARG_PASS);
	}
	...
}
```

下面示例中宏 `ISC_LANG_BEGINDECLS` 的存在导致下面的类型定义tree-sitter被错误当成 `struct dst_key dst_key_t;`
类型定义变成全局变量定义。从而没有解析出类型别名。后面需要解析 `dst_key_t` 类型下面的函数指针类型时解析中断。


```cpp
ISC_LANG_BEGINDECLS

/***
 *** Types
 ***/

/*%
 * The dst_key structure is opaque.  Applications should use the accessor
 * functions provided to retrieve key attributes.  If an application needs
 * to set attributes, new accessor functions will be written.
 */

typedef struct dst_key	   dst_key_t;
```

下面示例通过宏展开结构体定义，从而无法通过语法解析的方式分析出对应的field，影响后面的函数指针分析

```cpp
typedef struct dns_qpreader {
	DNS_QPREADER_FIELDS;
} dns_qpreader_t;
```

## 4.2.cyclonedds


下面示例中 `int sig __attribute__ ((unused)` 的 `__attribute__` 会导致解析错误

```cpp
static void log_stacktrace_sigh (int sig __attribute__ ((unused)) {...}
```

下面示例中call target的参数类型由于宏函数 `UNUSED_ARG` 的存在没有被正确解析出，导致类型匹配出错。

```cpp
static int proc_elem_open (void *varg, UNUSED_ARG (uintptr_t parentinfo), UNUSED_ARG (uintptr_t *eleminfo), const char *name, int line) {
    ...
}
```

## 4.3.dovecot

下面示例 `pam_const` 本来是个宏，预处理后为 `typedef void* pam_item_t;`，
但是这里错误解析成了 `pam_const` 和 `void` 的类型别名以及 `pam_item_t` 和 `pam_const*`。

```cpp
#  define pam_const
typedef pam_const void *pam_item_t;
```

## 4.4.hdf5

下面case宏 `H5E_BEGIN_TRY` 和 `H5E_END_TRY` 的存在导致下面 `if` 语句被错误识别为 `function_declarator`。

```cpp
H5E_BEGIN_TRY
{
   dataset = H5Dcreate2(FAKE_ID, DSET_NAME, H5T_STD_I32BE, space, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);
}
H5E_END_TRY

/* Create the dataset */
if ((dataset = H5Dcreate2(file, DSET_NAME, H5T_STD_I32BE, space, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT)) <
        0) ...
```

下面宏定义将函数名 `H5P__ocrt_pipeline_copy` 分配给宏 `H5O_CRT_PIPELINE_COPY` 导致分析address-taken function的时候没有分析出 `H5P__ocrt_pipeline_copy` 是取地址函数。

`unsigned H5_ATTR_UNUSED *des_flags` 的类型被错误解析为 `unsigned H5_ATTR_UNUSED*` 导致类型匹配失败。

```cpp
#define H5O_CRT_PIPELINE_COPY  H5P__ocrt_pipeline_copy

static H5FS_section_info_t *
H5MF__sect_deserialize(const H5FS_section_class_t *cls, const uint8_t H5_ATTR_UNUSED *buf, haddr_t sect_addr,
                       hsize_t sect_size, unsigned H5_ATTR_UNUSED *des_flags) {
                       
                       }
```

## 4.5.igraph

这个case中tree-sitter错误将这个全局变量定义解析为

- 一个全局变量声明 `static IGRAPH_THREAD_LOCAL igraph_error_handler_t`，
随后解析工具解析出变量 `igraph_error_handler_t` 的类型是 `IGRAPH_THREAD_LOCAL`。

- 一个变量定义 `*igraph_i_error_handler = 0;`。

```cpp

static IGRAPH_THREAD_LOCAL igraph_error_handler_t *igraph_i_error_handler = 0;
```

## 4.6.pjsip

下面示例中 `{status = PJ_EEXISTS; goto on_return;}` 的存在使得语法树解析错误，function definition在 `goto on_return` 截止。
使得接下来的代码都没在function definition范围内，丢失了对应的indirect-call。

```cpp
PJ_DEF(pj_status_t) pjsip_endpt_register_module( pjsip_endpoint *endpt,
                                                 pjsip_module *mod )
{
    ...
    /* Make sure that this module has not been registered. */
    PJ_ASSERT_ON_FAIL(  pj_list_find_node(&endpt->module_list, mod) == NULL,
                        {status = PJ_EEXISTS; goto on_return;});

    /* Make sure that no module with the same name has been registered. */
    PJ_ASSERT_ON_FAIL(  pj_list_search(&endpt->module_list, &mod->name, 
                                       &cmp_mod_name)==NULL,
                        {status = PJ_EEXISTS; goto on_return; });

    /* Find unused ID for this module. */
    for (i=0; i<PJ_ARRAY_SIZE(endpt->modules); ++i) {
        if (endpt->modules[i] == NULL)
            break;
    }
    ...
}
```


## 4.7.krb5

下面类型定义中，函数指针定义中包括了空宏 `KRB5_CALLCONV`，这个宏的存在使得函数指针解析错误。

```cpp
// krb5 case, KRB5_CALLCONV的存在使得类型解析错误
typedef struct gss_config {
    gss_OID_desc    mech_type;
    void *	    context;
    OM_uint32       (KRB5_CALLCONV *gss_acquire_cred)
	(
		    OM_uint32*,		/* minor_status */
		    gss_name_t,		/* desired_name */
		    OM_uint32,		/* time_req */
		    gss_OID_set,	/* desired_mechs */
		    int,		/* cred_usage */
		    gss_cred_id_t*,	/* output_cred_handle */
		    gss_OID_set*,	/* actual_mechs */
		    OM_uint32*		/* time_rec */
		    );
		    
    ...
} *gss_mechanism;
```

## 4.8.libucl

下面case中条件编译代码 `#ifdef`, `#else`, `#endif` 的存在导致tree-sitter没有展开 `ucl_object_free_internal (obj, false, ucl_object_dtor_unref);` 的AST。
也就是一个AST终端节点对应一个调用语句，这使得没有分析出 `ucl_object_dtor_unref` 是address-taken function从而导致没有分析出对应的call target。

```cpp
static void
ucl_object_dtor_unref_single (ucl_object_t *obj)
{
	if (obj != NULL) {
#ifdef HAVE_ATOMIC_BUILTINS
		unsigned int rc = __sync_sub_and_fetch (&obj->ref, 1);
		if (rc == 0) {
#else
		if (--obj->ref == 0) {
#endif
			ucl_object_free_internal (obj, false, ucl_object_dtor_unref);
		}
	}
}
```

# 5.Type Cast Case

## 5.1.void cast

`void*` --> `fuzzer_context*`

```cpp
// indirect-call
typedef void timeout_callback_t(void *context);

// call target
static void test_server_continue(struct fuzzer_context *ctx)
{
	//instead of simple io_loop_stop so as to free input io
	io_loop_stop_delayed(ctx->ioloop);
}
```


hdf5 case


```cpp
// address-taken function
static herr_t     H5E__print2(hid_t err_stack, FILE *stream);

// 函数指针
typedef herr_t (*H5E_auto2_t)(hid_t estack, void *client_data);
```

bluz case: `void* --> sdp_data_t*`

```cpp
// 函数指针类型定义
typedef void(*sdp_free_func_t)(void *);

void sdp_data_free(sdp_data_t *d) {
}
```