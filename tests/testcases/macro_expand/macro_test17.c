
#define ERREXIT1(cinfo, code, p1) \
  ((cinfo)->err->msg_code = (code), \
   (cinfo)->err->msg_parm.i[0] = (p1), \
   (*(cinfo)->err->error_exit) ((j_common_ptr)(cinfo)))

static void
start_pass_fdctmgr(j_compress_ptr cinfo) {
    int qtblno;
    ERREXIT1(cinfo, JERR_NO_QUANT_TABLE, qtblno);
}