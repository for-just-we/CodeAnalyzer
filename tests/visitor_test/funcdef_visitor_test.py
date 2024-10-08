from tree_sitter import Tree
from code_analyzer.schemas.ast_node import ASTNode
from code_analyzer.preprocessor.node_processor import processor

from code_analyzer.config import parser
from code_analyzer.visitors.base_func_visitor import FunctionDefVisitor

from typing import List

func_case1 = """
    static inline ngx_int_sig** add_sig(const char* data[], int& u, struct type1 c, type2 & d, const char* str, int* arr, ...) {
        return NULL;
    }
"""

func_case2 = """
    void ngx_cdecl ngx_conf_log_error(ngx_uint_t level, ngx_conf_t *cf, struct ngx_err_t* err, const char *fmt, ...)
{   const int& a = b; }
"""

func_case3 = """
   int
dlz_version(unsigned int *flags);

    static void * ngx_libc_cdecl ngx_regex_malloc(size_t size) { 
     int a = flag? 1: 0;
     init = uscfp[i]->peer.init_upstream
                                         ? uscfp[i]->peer.init_upstream
                                         : ngx_stream_upstream_init_round_robin;
                                         }
"""

func_case4 = """
    void ngx_queue_sort(ngx_queue_t *queue, ngx_int_t* (*cmp)(const ngx_queue_t *, const ngx_queue_t *)) {}
"""

func_case5 = """
    void ngx_cpuinfo(void) {}
"""

func_case6 = """
    int ngx_cdecl main(int argc, char *const *argv) {}
"""

func_case7 = """
static ngx_ssl_session_t *ngx_ssl_get_cached_session(ngx_ssl_conn_t *ssl_conn,
#if OPENSSL_VERSION_NUMBER >= 0x10100003L
    const
#endif
    u_char *id, int len, int *copy) {}
"""

func_case8 = """
static enum update_result uf_natint_255(struct ddsi_cfgst *cfgst, void *parent, struct cfgelem const * const cfgelem, int first, const char *value)
{
  return uf_int_min_max(cfgst, parent, cfgelem, first, value, 0, 255);
}
"""

# 用c解析器解析的出来而用c++不行
func_case9 = """
int test_run(void (*const test_functions[])(void))
{
    H5O_LOAD_NATIVE(f, 0, oh, &(oh->mesg[idx]), NULL)
}
"""

func_case10 = """
static struct event *event_passthrough_event(void)
{
	struct event *event = last_passthrough_event();
	event_last_passthrough = NULL;
	return event;
}
"""

func_case11 = """
static herr_t
H5F__close_cb(H5VL_object_t *file_vol_obj, void **request)
{
    herr_t ret_value = SUCCEED; /* Return value */

    FUNC_ENTER_PACKAGE

    /* Sanity check */
    assert(file_vol_obj);

    /* Close the file */
    if (H5VL_file_close(file_vol_obj, H5P_DATASET_XFER_DEFAULT, request) < 0)
        HGOTO_ERROR(H5E_FILE, H5E_CANTCLOSEFILE, FAIL, "unable to close file");

    /* Free the VOL object; it is unnecessary to unwrap the VOL
     * object before freeing it, as the object was not wrapped */
    if (H5VL_free_object(file_vol_obj) < 0)
        HGOTO_ERROR(H5E_FILE, H5E_CANTDEC, FAIL, "unable to free VOL object");

done:
    FUNC_LEAVE_NOAPI(ret_value)
}

static herr_t
H5T__close_cb(H5T_t *dt, void **request)
{
    herr_t ret_value = SUCCEED; /* Return value */

    FUNC_ENTER_PACKAGE

    /* Sanity check */
    assert(dt);
    assert(dt->shared);

    /* If this datatype is VOL-managed (i.e.: has a VOL object),
     * close it through the VOL connector.
     */
    if (NULL != dt->vol_obj) {
        /* Close the connector-managed datatype data */
        if (H5VL_datatype_close(dt->vol_obj, H5P_DATASET_XFER_DEFAULT, request) < 0)
            HGOTO_ERROR(H5E_DATATYPE, H5E_CLOSEERROR, FAIL, "unable to close datatype");

        /* Free the VOL object */
        if (H5VL_free_object(dt->vol_obj) < 0)
            HGOTO_ERROR(H5E_ATTR, H5E_CANTDEC, FAIL, "unable to free VOL object");
        dt->vol_obj = NULL;
    } /* end if */

    /* Close the datatype */
    if (H5T_close(dt) < 0)
        HGOTO_ERROR(H5E_DATATYPE, H5E_CLOSEERROR, FAIL, "unable to close datatype");

done:
    FUNC_LEAVE_NOAPI(ret_value)
}
"""

func_case12 = """
METHODDEF(void)
simple_upscale(j_decompress_ptr cinfo,
               JDIFFROW diff_buf, _JSAMPROW output_buf, JDIMENSION width)
{
  do {
    *output_buf++ = (_JSAMPLE)(*diff_buf++ << cinfo->Al);
  } while (--width);
}
"""

func_case13 = """void

f1
(int x) { 
    if(cond) 
        x = 1; 
    else 
    x = 2; 
    
    do {
    } while(x--);
    
    for (int i = 0; i < x; i++) {
    }
    
    while(x++) {
    
    }
    
    switch(x) {
        case 0:
        break;
        case 1:
        break;
        default:
        break;
    }
}
"""

func_case14 = """
static void *pool_system_malloc(pool_t pool ATTR_UNUSED, size_t size) {
    // yes
}
"""

func_case15 = """
herr_t
H5VL_init_phase2(void) {
    // yes
}
"""

func_case16 = """
isc_result_t
dns_rdataset_next(dns_rdataset_t *rdataset) {
	/*
	 * Move the rdata cursor to the next rdata in the rdataset (if any).
	 */

	REQUIRE(DNS_RDATASET_VALID(rdataset));
	REQUIRE(rdataset->methods != NULL);
	REQUIRE(rdataset->methods->next != NULL);

	return ((rdataset->methods->next)(rdataset));
}
"""

func_case17 = """
void
dns__rbtdb_closeversion(dns_db_t *db, dns_dbversion_t **versionp,
			bool commit DNS__DB_FLARG) {}
"""

func_case18 = """
static herr_t
H5AC__check_if_write_permitted(const H5F_t
#ifndef H5_HAVE_PARALLEL
                                   H5_ATTR_UNUSED
#endif /* H5_HAVE_PARALLEL */
                                       *f,
                               bool    *write_permitted_ptr) {
                               }
"""

# 可变参数
func_case19 = """
void
isc_error_unexpected(const char *arg, int num, const char *arg1, const char *arg2, ...) {
}

static void
parser_complain(cfg_parser_t *pctx, bool is_warning, unsigned int flags,
		const char *format, va_list args) {
}
"""

def testFuncDef():
    func_decls = [func_case1, func_case2, func_case3, func_case4, func_case5, func_case6, func_case7, func_case8,
                  func_case9, func_case10, func_case11, func_case12, func_case13, func_case14, func_case15,
                  func_case16, func_case17, func_case18, func_case19]
    for i, decl in enumerate(func_decls):
        tree: Tree = parser.parse(decl.encode("utf-8"))
        root_node: ASTNode = processor.visit(tree.root_node)
        func_visitor = FunctionDefVisitor()
        func_visitor.traverse_node(root_node)
    pass

if __name__ == '__main__':
    testFuncDef()