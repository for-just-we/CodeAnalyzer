from tree_sitter import Tree

from code_analyzer.config import parser
from code_analyzer.visitors.global_visitor import GlobalVisitor

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

global_decl_case2 = """
static const int a;
char* b = "aaaa";
static int* p[];
int (*p)[];
const struct Node* node;
int* (*add)(int a, int b);
"""

global_decl_case3 = """
static void (*const test_functions[])(void) = {
		test_qp_decoder,
		NULL
	};
"""

global_4 = """
event_create_passthrough(cmd->context.event)->
		set_name("smtp_server_command_started");
"""

global_5 = """
#define $LINE                 MakeString( Stringize, __LINE__ )
"""

if __name__ == '__main__':
    tree: Tree = parser.parse(global_4.encode("utf-8"))
    visitor = GlobalVisitor()
    visitor.walk(tree)
    pass