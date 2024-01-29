
#define LOADPTR(PTR, PTRINFO)                                           \
    (assert((PTRINFO)->loadptr != NULL), (PTRINFO)->loadptr(PTR))

struct ptr_info {
    void *(*loadptr)(const void *);
    void (*storeptr)(void *, void *);
    const struct atype_info *basetype;
};

static void
free_atype(const struct atype_info *a, void *val) {
    const struct ptr_info *ptrinfo = a->tinfo;
    LOADPTR(val, ptrinfo);
}