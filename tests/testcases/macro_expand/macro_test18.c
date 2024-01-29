
#define MAKESTMT(stuff)         do { stuff } while (0)

#define TRACEMS4(cinfo, lvl, code, p1, p2, p3, p4) \
  MAKESTMT(int *_mp = (cinfo)->err->msg_parm.i; \
           _mp[0] = (p1);  _mp[1] = (p2);  _mp[2] = (p3);  _mp[3] = (p4); \
           (cinfo)->err->msg_code = (code); \
           (*(cinfo)->err->emit_message) ((j_common_ptr)(cinfo), (lvl)); )


int
get_sof(j_decompress_ptr cinfo, boolean is_prog, boolean is_lossless,
        boolean is_arith) {
    TRACEMS4(cinfo, 1, JTRC_SOF, cinfo->unread_marker,
           (int)cinfo->image_width, (int)cinfo->image_height,
           cinfo->num_components);
}