from tree_sitter import Tree

from code_analyzer.schemas.ast_node import ASTNode
from code_analyzer.config import parser
from code_analyzer.visitors.global_visitor import GlobalVisitor
from code_analyzer.preprocessor.node_processor import processor

from typing import List

visitor = GlobalVisitor()

def testMacro():
    macros: str = """
    #define Max1(_a, b)
    #define Max2(_a, b)
    #define Max3(_a, b) _a >= b ? _a : b
    #define ngx_add_event        ngx_event_actions.add
    #define _NGX_ARRAY_H_INCLUDED_
    """
    tree: Tree = parser.parse(macros.encode("utf-8"))


    root_node: ASTNode = processor.visit(tree.root_node)
    visitor.traverse_node(root_node)
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
typedef int (* const secstream_protocol_connect_munge_t)(lws_ss_handle_t *h,
		char *buf, size_t len, struct lws_client_connect_info *i,
		union lws_ss_contemp *ct);
"""

global_init_decl1 = """
const cairo_font_face_backend_t _cairo_ft_font_face_backend = {
    CAIRO_FONT_TYPE_FT,
#if CAIRO_HAS_FC_FONT
    _cairo_ft_font_face_create_for_toy,
#else
    NULL,
#endif
    _cairo_ft_font_face_destroy,
    _cairo_ft_font_face_scaled_font_create,
    _cairo_ft_font_face_get_implementation
};
"""

func_array_decl = """
static int (*write_f[SYM_NUM]) (hashtab_key_t key, hashtab_datum_t datum,
				void *datap) = {
common_write, class_write, role_write, type_write, user_write,
	    cond_write_bool, sens_write, cat_write,};
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
                Union_case1,
                struct_case1,
                global_decl_case2,
                global_init_decl1,
                func_array_decl]

    for i, typeDef in enumerate(typeDefs):
        print(typeDef)
        tree: Tree = parser.parse(typeDef.encode("utf-8"))
        ast_node: ASTNode = processor.visit(tree.root_node)
        visitor.traverse_node(ast_node)
    print()

global_field_expr = """var1->f1->f2();"""

func_pointer_decl = """
struct dns_rdatacallbacks {
	unsigned int magic;

	/*%
	 * dns_load_master calls this when it has rdatasets to commit.
	 */
	dns_addrdatasetfunc_t add;

	/*%
	 * dns_master_load*() call this when loading a raw zonefile,
	 * to pass back information obtained from the file header
	 */
	dns_rawdatafunc_t rawdata;
	dns_zone_t	 *zone;

	/*%
	 * dns_load_master / dns_rdata_fromtext call this to issue a error.
	 */
	void (*error)(struct dns_rdatacallbacks *, const char *, ...);
	/*%
	 * dns_load_master / dns_rdata_fromtext call this to issue a warning.
	 */
	void (*warn)(struct dns_rdatacallbacks *, const char *, ...);
	/*%
	 * Private data handles for use by the above callback functions.
	 */
	void *add_private;
	void *error_private;
	void *warn_private;
};
"""

struct_def = """
struct decoder_t
{
    struct vlc_object_t obj;

    /* Module properties */
    module_t *          p_module;
    void               *p_sys;

    /* Input format ie from demuxer (XXX: a lot of fields could be invalid),
       cannot be NULL */
    const es_format_t   *fmt_in;

    /* Output format of decoder/packetizer */
    es_format_t         fmt_out;

    /* Tell the decoder if it is allowed to drop frames */
    bool                b_frame_drop_allowed;

    /**
     * Number of extra (ie in addition to the DPB) picture buffers
     * needed for decoding.
     */
    int                 i_extra_picture_buffers;

    union
    {
#       define VLCDEC_SUCCESS   VLC_SUCCESS
#       define VLCDEC_ECRITICAL VLC_EGENERIC
#       define VLCDEC_RELOAD    (-100)
        /* This function is called to decode one packetized block.
         *
         * The module implementation will own the input block (p_block) and should
         * process and release it. Depending of the decoder type, the module should
         * send output frames/blocks via decoder_QueueVideo(), decoder_QueueAudio()
         * or decoder_QueueSub().
         *
         * If frame is NULL, the decoder asks the module to drain itself. The
         * module should return all available output frames/block via the queue
         * functions.
         *
         * Return values can be:
         *  VLCDEC_SUCCESS: pf_decode will be called again
         *  VLCDEC_ECRITICAL: in case of critical error, pf_decode won't be called
         *  again.
         *  VLCDEC_RELOAD: Request that the decoder should be reloaded. The current
         *  module will be unloaded. Reloading a module may cause a loss of frames.
         *  When returning this status, the implementation shouldn't release or
         *  modify the frame in argument (The same frame will be feed to the
         *  next decoder module).
         */
        int             ( * pf_decode )   ( decoder_t *, vlc_frame_t *frame );

        /* This function is called in a loop with the same pp_block argument until
         * it returns NULL. This allows a module implementation to return more than
         * one output blocks for one input block.
         *
         * pp_block or *pp_block can be NULL.
         *
         * If pp_block and *pp_block are not NULL, the module implementation will
         * own the input block (*pp_block) and should process and release it. The
         * module can also process a part of the block. In that case, it should
         * modify (*ppframe)->p_buffer/i_buffer accordingly and return a valid
         * output block. The module can also set *ppframe to NULL when the input
         * block is consumed.
         *
         * If ppframe is not NULL but *ppframe is NULL, a previous call of the pf
         * function has set the *ppframe to NULL. Here, the module can return new
         * output block for the same, already processed, input block (the
         * pf_packetize function will be called as long as the module return an
         * output block).
         *
         * When the pf function returns NULL, the next call to this function will
         * have a new a valid ppframe (if the packetizer is not drained).
         *
         * If ppframe is NULL, the packetizer asks the module to drain itself. In
         * that case, the module has to return all output frames available (the
         * pf_packetize function will be called as long as the module return an
         * output block).
         */
        vlc_frame_t *   ( * pf_packetize )( decoder_t *, vlc_frame_t  **ppframe );
    };

    /* */
    void                ( * pf_flush ) ( decoder_t * );

    /* Closed Caption (CEA 608/708) extraction.
     * If set, it *may* be called after pf_packetize returned data. It should
     * return CC for the pictures returned by the last pf_packetize call only,
     * channel bitmaps will be used to known which cc channel are present (but
     * globaly, not necessary for the current packet. Video decoders should use
     * the decoder_QueueCc() function to pass closed captions. */
    vlc_frame_t *       ( * pf_get_cc )      ( decoder_t *, decoder_cc_desc_t * );

    /* Meta data at codec level
     *  The decoder owner set it back to NULL once it has retrieved what it needs.
     *  The decoder owner is responsible of its release except when you overwrite it.
     */
    vlc_meta_t          *p_description;

    /* Private structure for the owner of the decoder */
    const struct decoder_owner_callbacks *cbs;
};
"""

muti_decl = """
struct A a = {1, 2}, b = {2, 3}, c;
"""

decl_2 = """
struct piddesc const * const table = piddesc_tables_all[k];
struct flagset * const fs_dst = (entry->flags & PDF_QOS) ? &qfs_dst : &pfs_dst;
"""

union_decl = """
union bpf_iter_link_info {
	struct {
		__u32	map_fd;
	} map;
};
"""

struct_decl = """
struct isc_sockaddr {
	union {
		struct sockaddr		sa;
		struct sockaddr_in	sin;
		struct sockaddr_in6	sin6;
		struct sockaddr_storage ss;
	} type;
	unsigned int length; /* XXXRTH beginning? */
	ISC_LINK(struct isc_sockaddr) link;
};
"""

struct_decl1 = """
struct A {
    int common; // 共享的内存空间
    struct B{
        int a;
        char b;
        float c;
    };
};
"""

def testsingle():
    tree: Tree = parser.parse(struct_def.encode("utf-8"))
    root_node = processor.visit(tree.root_node)
    visitor.traverse_node(root_node)
    pass

modifier_decl = """
inline int add(int a, int b) {
    return a + b;
}
extern double a;

_Alignas(16) int a;

double _Complex z = 3.0 + 4.0 * I;

_Imaginary double ci = 3.0i;

void foo(int* restrict a, int* restrict b);

_Thread_local int thread_local_variable;

_Atomic int atomic_variable;

_Noreturn void die(void) {
    exit(1); // die函数不会返回
}

void status_prompt_menu_callback(__unused struct menu *menu, u_int idx, key_code key, void *data) {
}
"""

enum_decl = """
enum window_copy_cmd_action {
	WINDOW_COPY_CMD_NOTHING,
	WINDOW_COPY_CMD_REDRAW,
	WINDOW_COPY_CMD_CANCEL,
};

enum window_copy_cmd_action wind;

enum week { Mon=1, Tue, Wed, Thu, Fri Sat, Sun} days;

typedef enum { Mon=1, Tue, Wed, Thu, Fri Sat, Sun} Workdays;

enum {Yellow, Blue}* colors;
"""

if __name__ == '__main__':
    # testTypeDef()
    tree: Tree = parser.parse(func_array_decl.encode("utf-8"))
    ast_node: ASTNode = processor.visit(tree.root_node)
    global_visitor = GlobalVisitor()
    global_visitor.traverse_node(ast_node)
    pass