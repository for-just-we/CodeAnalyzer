
#define ONIGENC_MBC_ENC_LEN(enc,p)             (enc)->mbc_enc_len(p)

#define enclen(enc,p)          ONIGENC_MBC_ENC_LEN(enc,p)

static int
compile_length_string_node(Node* node, regex_t* reg) {
    UChar *p;
    OnigEncoding enc = reg->enc;
    enclen(enc, p);
}