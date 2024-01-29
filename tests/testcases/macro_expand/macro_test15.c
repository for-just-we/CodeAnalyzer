#define ONIGENC_MBC_TO_CODE(enc,p,end)         (enc)->mbc_to_code((p),(end))

typedef struct OnigEncodingTypeST {
  int    (*mbc_enc_len)(const OnigUChar* p);
  const char*   name;
  int           max_enc_len;
  int           min_enc_len;
  int    (*is_mbc_newline)(const OnigUChar* p, const OnigUChar* end);
  OnigCodePoint (*mbc_to_code)(const OnigUChar* p, const OnigUChar* end);
  int    (*code_to_mbclen)(OnigCodePoint code);
  int    (*code_to_mbc)(OnigCodePoint code, OnigUChar *buf);
  int    (*mbc_case_fold)(OnigCaseFoldType flag, const OnigUChar** pp, const OnigUChar* end, OnigUChar* to);
  int    (*apply_all_case_fold)(OnigCaseFoldType flag, OnigApplyAllCaseFoldFunc f, void* arg);
  int    (*get_case_fold_codes_by_str)(OnigCaseFoldType flag, const OnigUChar* p, const OnigUChar* end, OnigCaseFoldCodeItem acs[]);
  int    (*property_name_to_ctype)(struct OnigEncodingTypeST* enc, OnigUChar* p, OnigUChar* end);
  int    (*is_code_ctype)(OnigCodePoint code, OnigCtype ctype);
  int    (*get_ctype_code_range)(OnigCtype ctype, OnigCodePoint* sb_out, const OnigCodePoint* ranges[]);
  OnigUChar* (*left_adjust_char_head)(const OnigUChar* start, const OnigUChar* p);
  int    (*is_allowed_reverse_match)(const OnigUChar* p, const OnigUChar* end);
  int    (*init)(void);
  int    (*is_initialized)(void);
  int    (*is_valid_mbc_string)(const OnigUChar* s, const OnigUChar* end);
  unsigned int flag;
  OnigCodePoint sb_range;
  int index;
} OnigEncodingType;

typedef OnigEncodingType* OnigEncoding;

static void
print_enc_string(FILE* fp, OnigEncoding enc,
                 const UChar *s, const UChar *end) {
    const UChar *p;
    ONIGENC_MBC_TO_CODE(enc, p, end);
}