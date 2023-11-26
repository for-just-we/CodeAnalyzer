# 1.类型分析

下面步骤(1)-(3)依旧基于传统分析，(4)开始涉及LLM。同时(1)-(4)属于一个参数一个参数的比较类型，(5)-(6)属于让LLM对类型相关的文本进行整体性比对。

- (1).首先比较调用点的各个参数以及call target各个参数的类型，如果能够比较出结果，那么直接返回 `true`，比较不出，则尝试 (2)

- (2).找到调用点对应的函数指针声明出，比较函数指针声明和call target匹不匹配，如果非常匹配，则返回 `true`，比较不出，则尝试 (3)。

- (3).开始进行 `cast` 分析，当前步骤依旧采用规则分析：如果比较的类型有结构体类型，那么进一步查看当前两个类型是否存在包含关系，如果存在包含关系，那么则返回 `true`，否则尝试 (4)。

- (4).通过LLM分析函数指针声明的类型和call target的类型是否有相似处，选取能够匹配的target。

## 1.1.传统类型比对

1.用传统严格类型匹配方法比较调用点和call target的参数

找出indirect-call对应的call expression各个实参的声明，提取类型。下面示例中参数类型为 `ngx_cycle_t*`，则所有支持一个参数的且类型为 `ngx_cycle_t*` 的函数为潜在调用目标。

```cpp
ngx_cycle_t *cycle;
cycle->modules[i]->init_module(cycle)
```

对于参数类型求解，采用以下方法（通过递归求解）:

- 如果参数是一个 `identifer` 类型表达式，表示引用了一个变量，那么直接在局部、全局变量表搜索对应变量声明，查询类型。

- 如果参数是一个 `field_expression` 类型表达式，表示访问了结构体，那么首先求解 `base` 变量的类型，随后查询对应 `field` 的类型。比如变量声明 `ngx_module_t *module;` 和  `module->ctx_index`，求解类型的时候先查出 `module` 类型为 `ngx_module*`，随后在 `ngx_module` 类型定义下找出 `ctx_index` 类型为 `ngx_uint_t`。

- 如果是 `subscript_expression` 或者 `pointer_expression`，表示进行了数组或者指针访问，只需将 `base` 变量类型pointer_level减1即可，比如访问 `int` 数组，那么对应类型就是 `int`。

- 其它类型，返回 `unknown_type`。

2.找出对应函数指针的声明，求解类型

(a)在求解参数类型时容易出错，比如 `(*cf->handler)(cf, NULL, cf->handler_conf);`，`NULL` 可能是一个指针类型，但是不知道是什么指针，因此第2个参数类型求解不出来，这个时候就需要知道 `cf->handler` 的函数指针声明时候的类型。这里 `handler` 声明为 `ngx_conf_handler_pt handler;`, `typedef char *(*ngx_conf_handler_pt)(ngx_conf_t *cf, ngx_command_t *dummy, void *conf);`，可知，函数指针参数类型为 `(ngx_conf_t*, ngx_command_t*, void* )`。


可能会出现函数指针声明的位置：`typedef`，`struct`定义，全局变量定义，局部变量和函数参数定义。


## 1.2.cast分析

涉及到cast的例子的类型比对其实我没有在benchmark中找到，但为了sound还是抛出了一个类型分析策略

cast分析主要在(3)-(4)步，这里的分析和之前类似，依旧是比对参数类型。当比对两个参数类型的时候，如果无法用严格类型匹配推断出当前比对两个类型，那么则进行cast分析。

当前步骤依旧是逐个参数逐个参数比对类型，同时在当前cast分析，只分析涉及到结构体的cast，对于 `long`, `int` 这些原生类型转换不在当前步骤处理。

insight：结构体之间或者结构体和其它类型的转换通常涉及两种情况（**Note:** 通常cast都是指针类型，如果不是指针类型由于每个结构体类型占用内存空间几乎都不一样非常容易发生错误）：

- 类型包含

- 父类子类转换

1.类型包含：下面示例中 `ngx_str_node_t` 的第一个field的类型是 `ngx_rbtree_node_t`，同时在程序中发现了从 `ngx_str_node_t*` 指针cast到 `ngx_rbtree_node_t*` 的情况，这属于典型的类型包含。这种转换通常合法，推测主要的用途就是用另一种方式访问结构体的某些field。而且几乎所有这类cast中，**被包含类型**是包含类型的**第一个field**。

solution：步骤(3)用来处理这类case，通常无需LLM，如果有结构体类型，分析该结构体第1个field是不是另外一个类型就行。如果是则返回 `true`，否则继续分析是否是父类子类转换情况。

```cpp
typedef struct {
	ngx_rbtree_node_t node;
	ngx_str_t str;
} ngx_str_node_t;

typedef struct ngx_rbtree_node_s ngx_rbtree_node_t;

struct ngx_rbtree_node_s {
	ngx_rbtree_key_t key;
	ngx_rbtree_node_t *left;
	ngx_rbtree_node_t *right;
	ngx_rbtree_node_t *parent;
	u_char color;
	u_char data;
};
```

2.父类子类转换：这类case更加复杂，通常涉及到的两个 `struct` 指针类型。下面示例中 `generic_operation` 是 `accept_operation` 和 `read_operation` 的父类。但是无法通过简单的规则比较判断，而通过LLM分析可以大致判断：

- `generic_operation` 看起来像是 `accept_operation` 和 `read_operation` 的一种抽象。

- field都包含 `PJ_DECL_LIST_MEMBER(struct generic_operation);` 和 `pj_ioqueue_operation_e op;`，存在相似性。这一步中 `PJ_DECL_LIST_MEMBER` 是个宏定义，展开分析非常复杂，最好的方式就是通过LLM判断这两个类型是否存在相似性。

solution: 对于两个结构体指针类型，把两个 `struct` 类型定义喂给大模型，让其判断是否是父类子类关系。

```cpp
struct generic_operation
{
	PJ_DECL_LIST_MEMBER(struct generic_operation);
	pj_ioqueue_operation_e op;
};

struct accept_operation
{
	PJ_DECL_LIST_MEMBER(struct accept_operation);
	pj_ioqueue_operation_e op;

	pj_sock_t *accept_fd;
	pj_sockaddr_t *local_addr;
	pj_sockaddr_t *rmt_addr;
	int *addrlen;
};

struct read_operation
{
	PJ_DECL_LIST_MEMBER(struct read_operation);
	pj_ioqueue_operation_e  ;

	void *buf;
	pj_size_t size;
	unsigned flags;
	pj_sockaddr_t *rmt_addr;
	int *rmt_addrlen;
};
```


父类子类的一个更加极端的case如下：`Node` 是 `BagNode` 的父类，但是很明显 `Node` 的定义比 `BagNode` 复杂的多。


```cpp
typedef struct _Node {
	union {
		struct {
			NodeType node_type;
			int status;
			struct _Node* parent;
			struct _Node* body;
		} base;

		StrNode str;
		CClassNode cclass;
		QuantNode quant;
		BagNode bag;
		BackRefNode backref;
		AnchorNode anchor;
		ConsAltNode cons;
		CtypeNode ctype;
#ifdef USE_CALL
		CallNode call;
#endif
		GimmickNode gimmick;
	} u;
} Node;


typedef struct {
	NodeType node_type;
	int status;
	struct _Node* parent;
	struct _Node* body;

	enum BagType type;
	union {
		struct {
			int regnum;
			AbsAddrType called_addr;
			int entry_count;
			int called_state;
		} m;
		struct {
			OnigOptionType options;
		} o;
		struct {
			/* body is condition */
			struct _Node* Then;
			struct _Node* Else;
		} te;
	};

	/* for multiple call reference */
	OnigLen min_len; /* min length (byte) */
	OnigLen max_len; /* max length (byte) */
	OnigLen min_char_len;
	OnigLen max_char_len;
	int opt_count; /* referenced count in optimize_nodes() */
} BagNode;
```


## 1.3.文本分析

如果当前declarator无法通过(1)-(4)步逐个的比对类型判断，那么