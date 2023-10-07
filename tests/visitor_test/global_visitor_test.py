from tree_sitter import Tree

from code_analyzer.config import parser
from code_analyzer.visitors.global_visitor import GlobalVisitor

from typing import List

visitor = GlobalVisitor()

def testMacro():
    macros: List[str] = ["#define Max()",
                         "#define Max(_a, b)",
                         "#define Max(_a, b) _a >= b ? _a : b",
                         "#define ngx_add_event        ngx_event_actions.add",
                         "#define _NGX_ARRAY_H_INCLUDED_"]
    for macro in macros:
        tree: Tree = parser.parse(macro.encode("utf-8"))
        visitor.walk(tree)

    pass

Union_case1 = """
typedef union {
    struct sockaddr           sockaddr;
    struct sockaddr_in        sockaddr_in;
#if (NGX_HAVE_INET6)
    struct sockaddr_in6       sockaddr_in6;
#endif
#if (NGX_HAVE_UNIX_DOMAIN)
    struct sockaddr_un        sockaddr_un;
#endif
} ngx_sockaddr_t;
"""

struct_case1 = """
typedef struct {
    ngx_uint_t                family;
    union {
        ngx_in_cidr_t         in;
#if (NGX_HAVE_INET6)
        ngx_in6_cidr_t        in6;
#endif
    } u;
} ngx_cidr_t;
"""

func_ptr_case1 = """
typedef char **(*ngx_conf_post_handler_pt) (ngx_conf_t *cf,
    void *data, void *conf);
"""

struct_case2 = """
typedef struct Person {
    int a;
}* Person_t;
"""

struct_case3 = """
typedef struct Person Person_t;
"""

type_decl_case1 = """
typedef const char *(*ngx_stream_geoip_variable_handler_pt)(GeoIP *,
    u_long addr);
"""

global_decl_case1 = """
static ngx_event_module_t  ngx_epoll_module_ctx = {
    &epoll_name,
    ngx_epoll_create_conf,               /* create configuration */
    ngx_epoll_init_conf,                 /* init configuration */

    {
        ngx_epoll_add_event,             /* add an event */
        ngx_epoll_del_event,             /* delete an event */
        ngx_epoll_add_event,             /* enable an event */
        ngx_epoll_del_event,             /* disable an event */
        ngx_epoll_add_connection,        /* add an connection */
        ngx_epoll_del_connection,        /* delete an connection */
#if (NGX_HAVE_EVENTFD)
        ngx_epoll_notify,                /* trigger a notify */
#else
        NULL,                            /* trigger a notify */
#endif
        ngx_epoll_process_events,        /* process the events */
        ngx_epoll_init,                  /* init the events */
        ngx_epoll_done,                  /* done the events */
    }
};
"""

macro_case1 = """
#define __APPLE_USE_RFC_3542    /* IPV6_PKTINFO */
"""

global_decl_case2 = """
typedef int (*next_proto_cb)(SSL *ssl, const unsigned char **out,
                             unsigned char *outlen, const unsigned char *in,
                             unsigned int inlen, void *arg);
typedef int (*next_proto_cb)(SSL *, const unsigned char **out,
                             unsigned char *outlen, const unsigned char *in,
                             unsigned int inlen, void *arg);
typedef int (* const secstream_protocol_connect_munge_t)(lws_ss_handle_t *h,
		char *buf, size_t len, struct lws_client_connect_info *i,
		union lws_ss_contemp *ct);
"""

def testTypeDef():
    typeDefs = [macro_case1,
                type_decl_case1,
                global_decl_case1,
                "typedef int* uint_ptr;",
                "typedef int (*MathFunction)(int, int);",
                "typedef struct {\n"
                "    void        *elts;\n"
                "    ngx_uint_t   nelts;\n"
                "    size_t       size;\n"
                "    ngx_uint_t   nalloc;\n"
                "    ngx_pool_t  *pool;\n"
                "}* ngx_array_t;",
                "typedef ngx_int_t (*ngx_output_chain_filter_pt)(void *ctx, ngx_chain_t *in);",
                struct_case3,
                func_ptr_case1,
                Union_case1]

    for typeDef in typeDefs:
        print(typeDef)
        tree: Tree = parser.parse(typeDef.encode("utf-8"))
        visitor.walk(tree)

    pass

def testsingle():
    tree: Tree = parser.parse(global_decl_case2.encode("utf-8"))
    visitor.walk(tree)

if __name__ == '__main__':
    testsingle()