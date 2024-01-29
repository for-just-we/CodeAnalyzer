
#define HERROR(maj_id, min_id, ...)                                                                          \
    do {                                                                                                     \
        H5E_printf_stack(NULL, __FILE__, __func__, __LINE__, H5E_ERR_CLS_g, maj_id, min_id, __VA_ARGS__);    \
    } while (0)

#define HCOMMON_ERROR(maj, min, ...)                                                                         \
    do {                                                                                                     \
        HERROR(maj, min, __VA_ARGS__);                                                                       \
        err_occurred = true;                                                                                 \
        err_occurred = err_occurred; /* Shut GCC warnings up! */                                             \
    } while (0)


/* Set the fields in a shared message structure */
#define H5O_UPDATE_SHARED(SH_MESG, SH_TYPE, F, MSG_TYPE, CRT_IDX, OH_ADDR)                                   \
    {                                                                                                        \
        (SH_MESG)->type          = (SH_TYPE);                                                                \
        (SH_MESG)->file          = (F);                                                                      \
        (SH_MESG)->msg_type_id   = (MSG_TYPE);                                                               \
        (SH_MESG)->u.loc.index   = (CRT_IDX);                                                                \
        (SH_MESG)->u.loc.oh_addr = (OH_ADDR);                                                                \
    } /* end block */

#define HGOTO_ERROR(maj, min, ret_val, ...)                                                                  \
    do {                                                                                                     \
        HCOMMON_ERROR(maj, min, __VA_ARGS__);                                                                \
        HGOTO_DONE(ret_val);                                                                                 \
    } while (0)

#define INCR_NDECODE_DIRTIED(OH) (OH)->ndecode_dirtied++;

#define H5O_LOAD_NATIVE(F, IOF, OH, MSG, ERR)                                                                \
    if (NULL == (MSG)->native) {                                                                             \
        const H5O_msg_class_t *msg_type = (MSG)->type;                                                       \
        unsigned               ioflags  = (IOF);                                                             \
                                                                                                             \
        /* Decode the message */                                                                             \
        assert(msg_type->decode);                                                                            \
        if (NULL == ((MSG)->native = (msg_type->decode)((F), (OH), (MSG)->flags, &ioflags, (MSG)->raw_size,  \
                                                        (MSG)->raw)))                                        \
            HGOTO_ERROR(H5E_OHDR, H5E_CANTDECODE, ERR, "unable to decode message");                          \
                                                                                                             \
        /* Mark the message dirty if it was changed by decoding */                                           \
        if ((ioflags & H5O_DECODEIO_DIRTY) && (H5F_get_intent((F)) & H5F_ACC_RDWR)) {                        \
            (MSG)->dirty = true;                                                                             \
            /* Increment the count of messages dirtied by decoding, but */                                   \
            /* only ifndef NDEBUG */                                                                         \
            INCR_NDECODE_DIRTIED(OH)                                                                         \
        }                                                                                                    \
                                                                                                             \
        /* Set the message's "shared info", if it's shareable */                                             \
        if ((MSG)->flags & H5O_MSG_FLAG_SHAREABLE) {                                                         \
            assert(msg_type->share_flags &H5O_SHARE_IS_SHARABLE);                                            \
            H5O_UPDATE_SHARED((H5O_shared_t *)(MSG)->native, H5O_SHARE_TYPE_HERE, (F), msg_type->id,         \
                              (MSG)->crt_idx, (OH)->chunk[0].addr)                                           \
        } /* end if */                                                                                       \
                                                                                                             \
        /* Set the message's "creation index", if it has one */                                              \
        if (msg_type->set_crt_index) {                                                                       \
            /* Set the creation index for the message */                                                     \
            if ((msg_type->set_crt_index)((MSG)->native, (MSG)->crt_idx) < 0)                                \
                HGOTO_ERROR(H5E_OHDR, H5E_CANTSET, ERR, "unable to set creation index");                     \
        } /* end if */                                                                                       \
    }     /* end if */

struct H5F_t {
    char          *open_name;   /* Name used to open file                                       */
    char          *actual_name; /* Actual name of the file, after resolving symlinks, etc.      */
    H5F_shared_t  *shared;      /* The shared file info                                         */
    H5VL_object_t *vol_obj;     /* VOL object                                                   */
    unsigned       nopen_objs;  /* Number of open object headers                                */
    H5FO_t        *obj_count;   /* # of time each object is opened through top file structure   */
    bool           id_exists;   /* Whether an ID for this struct exists                         */
    bool           closing;     /* File is in the process of being closed                       */
    struct H5F_t  *parent;      /* Parent file that this file is mounted to                     */
    unsigned       nmounts;     /* Number of children mounted to this file                      */
};

typedef struct H5F_t H5F_t;


struct H5O_msg_class_t {
    unsigned    id;          /*message type ID on disk   */
    const char *name;        /*for debugging             */
    size_t      native_size; /*size of native message    */
    unsigned    share_flags; /* Message sharing settings */
    void *(*decode)(H5F_t *, H5O_t *, unsigned, unsigned *, size_t, const uint8_t *);
    herr_t (*encode)(H5F_t *, bool, uint8_t *, const void *);
    void *(*copy)(const void *, void *);                   /*copy native value         */
    size_t (*raw_size)(const H5F_t *, bool, const void *); /*sizeof encoded message	*/
    herr_t (*reset)(void *);                               /*free nested data structs  */
    herr_t (*free)(void *);                                /*free main data struct  */
    herr_t (*del)(H5F_t *, H5O_t *, void *);  /* Delete space in file referenced by this message */
    herr_t (*link)(H5F_t *, H5O_t *, void *); /* Increment any links in file reference by this message */
    herr_t (*set_share)(void *, const H5O_shared_t *); /* Set shared information */
    htri_t (*can_share)(const void *);                 /* Is message allowed to be shared? */
    herr_t (*pre_copy_file)(H5F_t *, const void *, bool *, const H5O_copy_t *,
                            void *); /*"pre copy" action when copying native value to file */
    void *(*copy_file)(H5F_t *, void *, H5F_t *, bool *, unsigned *, H5O_copy_t *,
                       void *); /*copy native value to file */
    herr_t (*post_copy_file)(const H5O_loc_t *, const void *, H5O_loc_t *, void *, unsigned *,
                             H5O_copy_t *); /*"post copy" action when copying native value to file */
    herr_t (*get_crt_index)(const void *, H5O_msg_crt_idx_t *); /* Get message's creation index */
    herr_t (*set_crt_index)(void *, H5O_msg_crt_idx_t);         /* Set message's creation index */
    herr_t (*debug)(H5F_t *, const void *, FILE *, int, int);
};


typedef struct H5O_msg_class_t H5O_msg_class_t;


void *
H5O_msg_read_oh(H5F_t *f, H5O_t *oh, unsigned type_id, void *mesg)
{
    const H5O_msg_class_t *type; /* Actual H5O class type for the ID */
    unsigned               idx;  /* Message's index in object header */
    void                  *ret_value = NULL;
    H5O_LOAD_NATIVE(f, 0, oh, &(oh->mesg[idx]), NULL)
}