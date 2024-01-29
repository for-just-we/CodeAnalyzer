
#define STR(off)                (ctx->text + (off))


#define MD_LOG(msg)                                                     \
    do {                                                                \
        if(ctx->parser.debug_log != NULL)                               \
            ctx->parser.debug_log((msg), ctx->userdata);                \
    } while(0)


#define MD_TEXT(type, str, size)                                            \
    do {                                                                    \
        if(size > 0) {                                                      \
            ret = ctx->parser.text((type), (str), (size), ctx->userdata);   \
            if(ret != 0) {                                                  \
                MD_LOG("Aborted from text() callback.");                    \
                goto abort;                                                 \
            }                                                               \
        }                                                                   \
    } while(0)


static int
md_process_inlines(MD_CTX* ctx, const MD_LINE* lines, int n_lines) {
    MD_TEXTTYPE text_type;
    OFF off = lines[0].beg;
    OFF tmp = (line->end < mark->beg ? line->end : mark->beg);
    MD_TEXT(text_type, STR(mark->beg+1), 1);
}