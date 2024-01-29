
#define VBUF_SPACE(v,n) ((v)->space((v),(n)))

#define VBUF_SKIP(bp) do { \
	while ((bp)->cnt > 0 && *(bp)->ptr) \
	    (bp)->ptr++, (bp)->cnt--; \
    } while (0)

#define VBUF_SNPRINTF(bp, sz, fmt, arg) do { \
	if (VBUF_SPACE((bp), (sz)) != 0) \
	    return (bp); \
	sprintf((char *) (bp)->ptr, (fmt), (arg)); \
	VBUF_SKIP(bp); \
    } while (0)

#define vstring_str(vp)		((char *) (vp)->vbuf.data)

struct VBUF {
    int     flags;			/* status, see below */
    unsigned char *data;		/* variable-length buffer */
    ssize_t len;			/* buffer length */
    ssize_t cnt;			/* bytes left to read/write */
    unsigned char *ptr;			/* read/write position */
    VBUF_GET_READY_FN get_ready;	/* read buffer empty action */
    VBUF_PUT_READY_FN put_ready;	/* write buffer full action */
    VBUF_SPACE_FN space;		/* request for buffer space */
};

typedef int (*VBUF_SPACE_FN) (VBUF *, ssize_t);

typedef struct VBUF VBUF;

VBUF   *vbuf_print(VBUF *bp, const char *format, va_list ap) {
    static VSTRING *fmt;		/* format specifier */
    int     width;			/* width and numerical precision */
    int     prec;			/* are signed for overflow defense */
    char   *s;
    VBUF_SNPRINTF(bp, (width > prec ? width : prec) + INT_SPACE,
				  vstring_str(fmt), s);
}