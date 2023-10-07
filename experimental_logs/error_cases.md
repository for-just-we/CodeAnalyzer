
# source code层面类型匹配失误的地方

`LOGIT(result);`，`LOGIT` 为宏定义，在该调用处只有一个参数被传入，但是其宏定义为：

```cpp
#define LOGIT(result)                                                 \
	if (result == ISC_R_NOMEMORY)                                 \
		(*callbacks->error)(callbacks, "dns_master_load: %s", \
				    isc_result_totext(result));       \
	else                                                          \
		(*callbacks->error)(callbacks, "%s: %s:%lu: %s",      \
				    "dns_master_load", source, line,  \
				    isc_result_totext(result))
```

也就是该函数调用需要至少支持3个参数的，最终调用的函数为，也就是至少2个参数。展开宏定义后匹配不上。

同时，有的function definition是宏定义扩展生成的，因为无法直接对预处理前的c文件解析得到

```cpp
static void
isclog_error_callback(dns_rdatacallbacks_t *callbacks, const char *fmt, ...)
```


另一种情况就是调用的函数不在当前project范围内。

然后还有c文件解析错误导致没有正常解析callee或者indirect-call的情况

类型匹配漏报情况统计：

| project    | 漏报情况 |
|----|----|
| nginx| 1外部调用 |
| bind9 | 1宏定义展开参数+6宏定义展开函数 |
| cyclonedds | 2解析错误 |
| dovecot | 4宏定义+1复合call |
| hdf5 | 4文件解析错误+2宏定义 |
| igraph | 3文件解析错误+13外部调用 |
| libdwarf | 47宏定义 |
| lxc | 1宏定义展开函数 | 
| md4c | 34宏定义展开 |



bind9

```
lib/dns/master.c:2113:2-宏定义展开后参数变多
lib/dns/dst_api.c:2327:9-调用func为宏定义展开函数
lib/dns/dst_api.c:747:10-调用func为宏定义展开函数
```

cyclonedds

```
src/ddsrt/src/xmlparser.c:641:14-调用project之外的func
```

dovecot

```
src/lib/connection.c:591:2-宏定义导致icall位置发生变化从而让ground-truth失效
src/lib-smtp/smtp-server-command.c:223:2-宏定义导致icall位置发生变化从而让ground-truth失效
src/lib-smtp/smtp-server-command.c:351:3-宏定义导致icall位置发生变化从而让ground-truth失效
src/lib/connection.c:813:32-宏定义导致icall位置发生变化从而让ground-truth失效 + 复合表达式调用造成ground-truth失误
src/lib/connection.c:816:2-宏定义导致icall位置发生变化从而让ground-truth失效
```

hdf5

```
src/H5.c:268:17-c文件解析错误
src/H5VLint.c:198:13-c文件解析错误
src/H5SL.c:818:19-c文件解析错误
src/H5SL.c:2089:26-c文件解析错误
src/H5Omessage.c:487:5-宏定义展开后参数变多
src/H5Omessage.c:1160:13-宏定义展开后参数变多
```

igraph

```
src/core/error.c:171:9-c文件未正确解析
src/core/error.c:282:9-c文件未正确解析
src/core/error.c:383:9-c文件未正确解析
src/internal/qsort.c:135:27-外部调用+宏定义扩展参数
src/internal/qsort.c:158:36-外部调用+宏定义扩展参数
src/internal/qsort.c:166:36-外部调用+宏定义扩展参数
src/internal/qsort.c:184:27-外部调用+宏定义扩展参数
src/isomorphism/bliss.cc:97:12-调用外部函数
src/isomorphism/bliss/graph.cc:625:26-调用外部函数
src/isomorphism/bliss/graph.cc:634:3-调用外部函数
src/isomorphism/bliss/graph.cc:675:3-调用外部函数
src/isomorphism/bliss/graph.cc:3973:37-调用外部函数
src/isomorphism/bliss/graph.cc:183:30-调用外部函数
src/isomorphism/bliss/graph.cc:189:30-调用外部函数
src/isomorphism/bliss/graph.cc:729:3-调用外部函数
src/isomorphism/bliss/graph.cc:420:26-调用外部函数
```

libdwarf

```
src/lib/libdwarf/dwarf_die_deliv.c:452:5-宏定义导致参数数量增加
src/lib/libdwarf/dwarf_die_deliv.c:319:5-宏定义导致参数数量增加
src/lib/libdwarf/dwarf_die_deliv.c:383:9-宏定义导致参数数量增加
src/lib/libdwarf/dwarf_die_deliv.c:387:9-宏定义导致参数数量增加
```