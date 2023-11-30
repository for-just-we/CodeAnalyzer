

static void
status_prompt_menu_callback(__unused struct menu *menu, u_int idx, key_code key,
    void *data) {
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