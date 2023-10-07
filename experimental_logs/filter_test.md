
尝试过用CodeBert或者VarCLR做简单过滤

# 1.VarCLR效果

## 1.1.类型相似度预测

因为变量名随机因素太多，而类型名往往语义相似性会强些，因此这里先用VarCLR进行类型名预测。

group1:

src: `char`, target: `{u_char, ssize_t, int, short, intptr, unsigned char}`

结果为: `0.64, 0.45, 0.90, 0.66, 0.79, 0.66`，可以看到 `u_char`，`unsigned char` 和 `char` 的相似度低于 `int` 和 `intptr`


group2:

src: `ngx_conf_t`, target: `{ngx_conf_s, ngx_module_t, ngx_module_s, ngx_log_t, ngx_log_s, ngx_event_t, ngx_event_s}`

结果为 `0.52, 0.70, 0.43, 0.54, 0.53, 0.86, 0.64`，VarCLR这里依旧产生了误报，`ngx_conf_s` 理应权重最高。

group 3:

src: `ngx_uint_t`, target: `{ngx_log_t, ngx_err_t, uintptr_t, ngx_int_t, unsigned long, unsigned int, int, u_char, ngx_conf_t, ngx_command_t}`

结果为 `0.95, 0.63, 0.64, 0.59, 0.54, 0.80, 0.58, 0.64, 0.64, 0.63`，可以看到VarCLR依旧有误报，分数最高的 `ngx_log_t` 毫无关系，而同名类型 `uintptr_t`, `unsigned long` 分数仅仅为0.64和0.54。而文本且语义相似的 `ngx_int_t` 分数也只有0.59。

因此可以得出结论用VarCLR来替代字符串匹配做type match可行性较低。

## 1.2.函数名分析

group1:

src: `handler`, target: `{ngx_load_module, ngx_resolver_log_error, ngx_http_fastcgi_lowat_check, ngx_http_upstream_rewrite_location, ngx_http_fastcgi_split_path_info}`

结果为 `0.32, 0.37, 0.45, 0.31, 0.32`，基于函数名过滤还是有些难度的。


group2:

src: `writer`, target: `{ngx_log_error,ngx_ssl_get_cached_session,ngx_http_ssl_npn_advertised,ngx_http_v2_filter_get_shadow,ngx_http_xslt_sax_external_subset,ngx_http_xslt_sax_error,ngx_log_memory_writer,ngx_http_log_error_handler,ngx_syslog_writer,ngx_ssl_password_callback}`

结果为: `0.30, 0.69, 0.71, 0.15, 0.38, 0.30, 0.34, 0.32, 0.17, 0.43`，最可能成为true positive的2个函数分数只有 `0.34`、`0.17`，分数最高的同样也是false positive。

# 2.CodeBert测试

callsite code: `log->handler(log, p, last - p)`

函数声明包括: 

```c
char *
ngx_conf_set_sec_slot(ngx_conf_t *cf, ngx_command_t *cmd, void *conf)

static u_char *
ngx_resolver_log_error(ngx_log_t *log, u_char *buf, size_t len)

static u_char *
ngx_http_log_error(ngx_log_t *log, u_char *buf, size_t len)

static char *
ngx_http_xslt_entities(ngx_conf_t *cf, ngx_command_t *cmd, void *conf)

static char *
ngx_http_try_files(ngx_conf_t *cf, ngx_command_t *cmd, void *conf)

static u_char *
ngx_http_v2_state_priority(ngx_http_v2_connection_t *h2c, u_char *pos,
    u_char *end)
    
static u_char *
ngx_http_v2_state_proxy_protocol(ngx_http_v2_connection_t *h2c, u_char *pos,
    u_char *end)
    
static ngx_int_t
ngx_http_geoip_country_variable(ngx_http_request_t *r,
    ngx_http_variable_value_t *v, uintptr_t data)
    
static ngx_int_t
ngx_http_variable_sent_last_modified(ngx_http_request_t *r,
    ngx_http_variable_value_t *v, uintptr_t data)
    
static char *
ngx_mail_smtp_merge_srv_conf(ngx_conf_t *cf, void *parent, void *child)
```

分析结果为: `0.96, 0.99, 0.94, 0.96, 0.96, 0.97, 0.95, 0.97, 0.96, 0.96`，可以看到分数基本一致，很难区分true/false positive。

往icallsite添加一些上下文信息: 

```c
ngx_log_t *log
u_char      *p, *last, *msg;
log->handler(log, p, last - p)
```

结果变为: `0.99, 0.99, 0.99, 0.99, 0.98, 0.99, 0.98, 0.99, 0.99, 0.99`，更难区分true/false positive。