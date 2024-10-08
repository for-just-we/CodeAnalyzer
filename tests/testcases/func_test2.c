#ifndef DDSI_UNUSED_H
#define DDSI_UNUSED_H

#ifdef __GNUC__
#define UNUSED_ARG(x) x __attribute__ ((unused))
#else

#define UNUSED_PARAM(param) param __unused__


// case from igraph，这个case中tree-sitter错误将这个全局变量定义解析为一个全局变量声明和一个变量定义。
static IGRAPH_THREAD_LOCAL igraph_error_handler_t *igraph_i_error_handler = 0;

static void
status_prompt_menu_callback(__unused struct menu *menu, u_int idx, key_code key,
    void *data) {
    fp = (ngx_flag_t *) (p + cmd->offset);
}

static int
ovpn_nl_cb_finish(struct nl_msg (*msg) __attribute__ ((unused)), void *arg) {
}

static cairo_test_status_t
record_replay (cairo_t *cr, cairo_t *(*func)(cairo_t *), int width, int height) {
}

static void CAIRO_BOILERPLATE_PRINTF_FORMAT(2,3)
_log (cairo_test_context_t *ctx,
      const char *fmt,
      ...) {
      }

// __attribute__((__unused__))这种GCC扩展语法无法用tree-sitter处理
static int
setup_env(void **unused __attribute__((__unused__))) {
	char *env = getenv("ISC_BENCHMARK_LOOPS");
	if (env != NULL) {
		loops = atoi(env);
	}
	assert_int_not_equal(loops, 0);

	env = getenv("ISC_BENCHMARK_DELAY");
	if (env != NULL) {
		delay_loop = atoi(env);
	}
	assert_int_not_equal(delay_loop, 0);

	return (0);
}


static isc_result_t
publish_key(dns_diff_t *diff, dns_dnsseckey_t *key, const dns_name_t *origin,
	    dns_ttl_t ttl, isc_mem_t *mctx,
	    void (*report)(const char *, ...) ISC_FORMAT_PRINTF(1, 2)) {
	    dns_rdata_ #_t *# = source;
}


void
dns_rdatalist_disassociate(dns_rdataset_t *rdataset DNS__DB_FLARG) {
	UNUSED(rdataset);
}

// 从hdf5收集的样本
static herr_t
H5P__ocrt_pipeline_copy(const char H5_ATTR_UNUSED *name, size_t H5_ATTR_UNUSED size, void *value) {
    ...
}

int a[] = {1, 2, 3, 4};

size_t
sudo_strlcpy(char * restrict dst, const char * restrict src, size_t dsize) {

}

static void default_log_func(
		__attribute__(( unused )) enum fuse_log_level level,
		const char *fmt, va_list ap)
{
	vfprintf(stderr, fmt, ap);
}

static OM_uint32 KRB5_CALLCONV
krb5_gss_inquire_attrs_for_mech(OM_uint32 *minor_status,
                                gss_const_OID mech,
                                gss_OID_set *mech_attrs,
                                gss_OID_set *known_mech_attrs){
                                }

static void none_crypt(UNUSED_PARAM(struct ssh_cipher_struct *cipher),
           void *in,
           void *out,
           size_t len)
{
    memcpy(out, in, len);
}