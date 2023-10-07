func_declarator1 = """
char *
ngx_conf_set_sec_slot(ngx_conf_t *cf, ngx_command_t *cmd, void *conf)
"""

func_declarator2 = """
static u_char *
ngx_resolver_log_error(ngx_log_t *log, u_char *buf, size_t len)
"""

func_declarator3 = """
static u_char *
ngx_http_log_error(ngx_log_t *log, u_char *buf, size_t len)
"""

func_declarator4 = """
static char *
ngx_http_xslt_entities(ngx_conf_t *cf, ngx_command_t *cmd, void *conf)
"""

func_declarator5 = """
static char *
ngx_http_try_files(ngx_conf_t *cf, ngx_command_t *cmd, void *conf)
"""

func_declarator6 = """
static u_char *
ngx_http_v2_state_priority(ngx_http_v2_connection_t *h2c, u_char *pos,
    u_char *end)
"""

func_declarator7 = """
static u_char *
ngx_http_v2_state_proxy_protocol(ngx_http_v2_connection_t *h2c, u_char *pos,
    u_char *end)
"""

func_declarator8 = """
static ngx_int_t
ngx_http_geoip_country_variable(ngx_http_request_t *r,
    ngx_http_variable_value_t *v, uintptr_t data)
"""

func_declarator9 = """
static ngx_int_t
ngx_http_variable_sent_last_modified(ngx_http_request_t *r,
    ngx_http_variable_value_t *v, uintptr_t data)
"""

func_declarator10 = """
static char *
ngx_mail_smtp_merge_srv_conf(ngx_conf_t *cf, void *parent, void *child)
"""