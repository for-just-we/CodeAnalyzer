
#define CHECK(expr) do { \
                        status=expr; if (status!=PJ_SUCCESS) return status; } \
                    while (0)

typedef pj_status_t (*pj_json_writer)(const char *s,
                                      unsigned size,
                                      void *user_data);

struct write_state
{
    pj_json_writer       writer;
    void                *user_data;
    char                 indent_buf[MAX_INDENT];
    int                  indent;
    char                 space[PJ_JSON_NAME_MIN_LEN];
};

static pj_status_t write_children(const pj_json_list *list,
                                  const char quotes[2],
                                  struct write_state *st) {
    CHECK( st->writer( "\n", 1, st->user_data) );
}