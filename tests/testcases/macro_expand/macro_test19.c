#define INPUT_RELOAD(cinfo) \
  ( next_input_byte = datasrc->next_input_byte, \
    bytes_in_buffer = datasrc->bytes_in_buffer )

#define MAKE_BYTE_AVAIL(cinfo, action) \
  if (bytes_in_buffer == 0) { \
    if (!(*datasrc->fill_input_buffer) (cinfo)) \
      { action; } \
    INPUT_RELOAD(cinfo); \
  }

#define MAKESTMT(stuff)         do { stuff } while (0)

#define INPUT_BYTE(cinfo, V, action) \
  MAKESTMT( MAKE_BYTE_AVAIL(cinfo, action); \
            bytes_in_buffer--; \
            V = *next_input_byte++; )

int
get_sof(j_decompress_ptr cinfo, boolean is_prog, boolean is_lossless,
        boolean is_arith) {
    INPUT_BYTE(cinfo, cinfo->data_precision, return FALSE);
}