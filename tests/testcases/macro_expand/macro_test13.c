
#define CALL_SMETHOD(obj, method, args...) GET_SMETHODS(obj)->method(obj, ## args)
#define CALL_SMETHOD1(obj, method, ...) GET_SMETHODS(obj)->method(obj)

#define GET_SMETHODS(obj) _Generic((obj), \
    struct rtpp_refcnt *: rtpp_refcnt_smethods, \
    struct rtpp_pearson_perfect *: rtpp_pearson_perfect_smethods, \
    struct rtpp_netaddr *: rtpp_netaddr_smethods, \
    struct rtpp_server *: rtpp_server_smethods, \
    struct rtpp_stats *: rtpp_stats_smethods, \
    struct rtpp_timed *: rtpp_timed_smethods, \
    struct rtpp_stream *: rtpp_stream_smethods, \
    struct rtpp_pcount *: rtpp_pcount_smethods, \
    struct rtpp_record *: rtpp_record_smethods, \
    struct rtpp_hash_table *: rtpp_hash_table_smethods, \
    struct rtpp_weakref *: rtpp_weakref_smethods, \
    struct rtpp_analyzer *: rtpp_analyzer_smethods, \
    struct rtpp_pcnt_strm *: rtpp_pcnt_strm_smethods, \
    struct rtpp_ttl *: rtpp_ttl_smethods, \
    struct rtpp_pipe *: rtpp_pipe_smethods, \
    struct rtpp_ringbuf *: rtpp_ringbuf_smethods, \
    struct rtpp_sessinfo *: rtpp_sessinfo_smethods, \
    struct rtpp_rw_lock *: rtpp_rw_lock_smethods, \
    struct rtpp_proc_servers *: rtpp_proc_servers_smethods, \
    struct rtpp_proc_wakeup *: rtpp_proc_wakeup_smethods, \
    struct pproc_manager *: pproc_manager_smethods \
)

static void
init_cstats(struct rtpp_stats *sobj, struct rtpp_command_stats *csp)
{
    CALL_SMETHOD(sobj, getidxbyname, "ncmds_rcvd");
}