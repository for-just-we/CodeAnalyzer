
#define CALL_METHOD(obj, method, args...) (obj)->method(obj, ## args)

static void
init_config_bail(struct rtpp_cfg *cfsp, int rval, const char *msg, int memdeb) {
    CALL_METHOD(cfsp->bindaddrs_cf, dtor);
}