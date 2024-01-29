
#define MD_LOG(msg)                                                     \
    do {                                                                \
        if(ctx->parser.debug_log != NULL)                               \
            ctx->parser.debug_log((msg), ctx->userdata);                \
    } while(0)


#define MD_ENTER_SPAN(type, arg)                                            \
    do {                                                                    \
        ret = ctx->parser.enter_span((type), (arg), ctx->userdata);         \
        if(ret != 0) {                                                      \
            MD_LOG("Aborted from enter_span() callback.");                  \
            goto abort;                                                     \
        }                                                                   \
    } while(0)

static int
md_enter_leave_span_a(MD_CTX* ctx, int enter, MD_SPANTYPE type,
                      const CHAR* dest, SZ dest_size, int prohibit_escapes_in_dest,
                      const CHAR* title, SZ title_size) {
    MD_ENTER_SPAN(type, &det);
}