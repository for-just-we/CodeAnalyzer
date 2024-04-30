
# 1.benchmarks

| project | compiled indirect-call num | indirect-call num in ground truth | compiled functions  | successful parsed functions | macro callsite |
| ---- |----|----|---- | ---- | ---- |
| bind9 | 592 | 46 | 6285 | 8791 | 1 |
| bluez | 1016 | 4 | 11719 | 17893 | 0 |
| cairo | 905 | 41 | 7450 | 7648 | 0 |
| cyclonedds | 898 | 47 | 9722 | 7907 | 0 |
| dovecot | 6241 | 60 | 42840 | 19029 | 11 |
| fwupd | 100 | 31 | 2846 | 8017 | 0 |
| hdf5 | 1592 | 94 | 5563 | 14008 | 2 |
| gdbm | 241 | 18 | 486 | 576 | 0 |
| gdk-pixbuf | 131 | 3 | 982 | 816 | 0 | 
| igraph | 983 | 19 | 5253 | 5679 | 2 |
| krb5 | 1044 | 18 | 6846 | 8485 | 8 |
| libdwarf | 402 | 202 | 1546 | 1996 | 185 | 
| libjpeg-turbo | 2890 | 462 | 2301 | 1479 | 200 |
| libbpf | 60 | 1 | 1196 | 1095 | 0 |
| libfuse | 133 | 1 | 1170 | 1025 | 0 |
| libpg_query | 200 | 11 | 4174 | 9170 | 0 |
| libsndfile | 150 | 8 | 1162 | 1672 | 0 | 
| libucl | 202 | 3 | 691 | 390 | 0 |
| libssh | 84 | 15 | 1337 | 2843 | 0 |
| librabbitmq | 14 | 6 | 557 | 308 | 0 |
| lua | 17 | 7 | 1079 | 1208 | 5 |
| lxc | 404 | 7 | 9316 | 2298 | 0 |
| md4c | 126 | 39 | 150 | 155 | 33 |
| mdbtools | 50 | 2 | 544 | 432 | 0 |
| nginx | 367 | 23 | 1656 | 3062 | 0 |
| open5gs | 7128 | 1 | 15704 | 15200 | 0 |
| opensips | 282 | 8 | 2788 | 10891 | 0 |
| oniguruma | 1006 | 268 | 1616 | 1014 | 160 |
| postfix | 458 | 4 | 2597 | 3406 | 1 |
| protobuf-c | 29 | 2 | 360 | 308 | 0 |
| pjsip | 811 | 43 | 7598 | 11058 | 19 |
| rtpproxy | 3092 | 161 | 3758 | 1806 | 152 |
| selinux | 1966 | 21 | 4457 | 6032 | 0 |
| sudo | 324 | 96 | 1952 | 3113 | 1 |
| tmux | 87 | 11 | 2301 | 2221 | 0 |
| vlc | 10698 | 1065 | 16483 | 19128 | 0 |


# 2.Macro Callsites

## 2.1.bind9

callsite: `LOGIT(result)`

macro:

```cpp
#define LOGIT(result)                                                 \
	if (result == ISC_R_NOMEMORY)                                 \
		(*callbacks->error)(callbacks, "dns_master_load: %s", \
				    isc_result_totext(result));       \
	else                                                          \
		(*callbacks->error)(callbacks, "%s: %s:%lu: %s",      \
				    "dns_master_load", source, line,  \
				    isc_result_totext(result))
```

## 2.2.dovecot

callsites:

```cpp
e_debug(e->event(), "Execute command");

unlikely((ret = _stream->flush(_stream))
```


macros:

```cpp
#define event_create_passthrough(parent) \
	event_create_passthrough((parent), __FILE__, __LINE__)

// _event是一个函数指针
#define e_debug(_event, ...) STMT_START { \
	struct event *_tmp_event = (_event); \
	if (event_want_debug(_tmp_event)) \
		e_debug(_tmp_event, __FILE__, __LINE__, __VA_ARGS__); \
	else \
		event_send_abort(_tmp_event); \
	} STMT_END
	
# define unlikely(expr) (__builtin_expect((expr) ? 1 : 0, 0) != 0)
# define unlikely(expr) expr
```

## 2.3.hdf5

callsite: 

- `H5O_LOAD_NATIVE(f, 0, oh, &(oh->mesg[idx]), NULL)`

macro:

```cpp
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
```

## 2.4.igraph

callsite: 

- `CMP(thunk, pl - es, pl)`

- `gmp_alloc (size * sizeof (mp_limb_t))`

macro:

```cpp
#define	CMP(t, x, y) (cmp((x), (y)))

#define gmp_alloc(size) ((*gmp_allocate_func)((size)))
```

## 2.5.krb5

callsite:

- `LOADPTR(val, ptrinfo)`

- `STOREPTR(NULL, ptrinfo, val)`

macro:

```cpp
#define LOADPTR(PTR, PTRINFO)                                           \
    (assert((PTRINFO)->loadptr != NULL), (PTRINFO)->loadptr(PTR))
    
#define STOREPTR(PTR, PTRINFO, VAL)                                     \
    (assert((PTRINFO)->storeptr != NULL), (PTRINFO)->storeptr(PTR, VAL))
```

## 2.6.lua

callsite:

- `callfrealloc(g, block, osize, 0)`

- `firsttry(g, block, osize, nsize)`

- `LUAI_TRY(L, &lj, (*f)(L, ud);)`

- `cast(LG *, (*f)(ud, NULL, LUA_TTHREAD, sizeof(LG)))`

macro:

```cpp
#define callfrealloc(g,block,os,ns) ((*g->frealloc)(g->ud, block, os, ns))

#define firsttry(g,block,os,ns)    callfrealloc(g, block, os, ns)

#define LUAI_TRY(L,c,a)		if (setjmp((c)->b) == 0) { a }

#define cast(t, exp)	((t)(exp))
```

## 2.7.sudo

callsite: 

- `debug_return_bool(def->callback(ctx, file, line, column, &def->sd_un, op))`

macro:

```cpp
# define sudo_debug_exit_bool(_func, _file, _line, _sys, _ret)		       \
    do {								       \
	sudo_debug_printf2(NULL, NULL, 0, (_sys) | SUDO_DEBUG_TRACE,	       \
	    "<- %s @ %s:%d := %s", (_func), (_file), (_line), (_ret) ? "true": "false");\
    } while (0)
   
#define debug_return_bool(ret)						       \
    do {								       \
	bool sudo_debug_ret = (ret);					       \
	sudo_debug_exit_bool(__func__, __FILE__, __LINE__, sudo_debug_subsys,  \
	    sudo_debug_ret);						       \
	return sudo_debug_ret;						       \
    } while (0)
```

## 2.8.postfix

callsite:

- `VBUF_SNPRINTF(bp, (width > prec ? width : prec) + INT_SPACE, vstring_str(fmt), s)`

macro:

```cpp
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
```

## 2.9.pjsip

callsite:

- `CHECK( st->writer( "\n", 1, st->user_data) )`

macro:

```cpp
#define CHECK(expr) do { \
                        status=expr; if (status!=PJ_SUCCESS) return status; } \
                    while (0)
```

## 2.10.md4c

callsite:

- `MD_LEAVE_SPAN(type, &det)`

- `MD_ENTER_SPAN(MD_SPAN_WIKILINK, &det)`

- `MD_TEXT(text_type, STR(mark->beg+1), 1)`

- `MD_ENTER_BLOCK(block->type, (void*) &det)`

- `MD_LEAVE_BLOCK(block->type, &det)`

macro

```cpp
#define MD_LOG(msg)                                                     \
    do {                                                                \
        if(ctx->parser.debug_log != NULL)                               \
            ctx->parser.debug_log((msg), ctx->userdata);                \
    } while(0)
    
#define MD_ENTER_BLOCK(type, arg)                                           \
    do {                                                                    \
        ret = ctx->parser.enter_block((type), (arg), ctx->userdata);        \
        if(ret != 0) {                                                      \
            MD_LOG("Aborted from enter_block() callback.");                 \
            goto abort;                                                     \
        }                                                                   \
    } while(0)

#define MD_LEAVE_BLOCK(type, arg)                                           \
    do {                                                                    \
        ret = ctx->parser.leave_block((type), (arg), ctx->userdata);        \
        if(ret != 0) {                                                      \
            MD_LOG("Aborted from leave_block() callback.");                 \
            goto abort;                                                     \
        }                                                                   \
    } while(0)

#define MD_ENTER_SPAN(type, arg)                                            \
    do {                                                                    \
        ret = ctx->parser.enter_span((type), (arg), ctx->userdata);         \
        if(ret != 0) {                                                      \
            MD_LOG("Aborted from enter_span() callback.");                  \
            goto abort;                                                     \
        }                                                                   \
    } while(0)

#define MD_LEAVE_SPAN(type, arg)                                            \
    do {                                                                    \
        ret = ctx->parser.leave_span((type), (arg), ctx->userdata);         \
        if(ret != 0) {                                                      \
            MD_LOG("Aborted from leave_span() callback.");                  \
            goto abort;                                                     \
        }                                                                   \
    } while(0)

#define MD_TEXT(type, str, size)                                            \
    do {                                                                    \
        if(size > 0) {                                                      \
            ret = ctx->parser.text((type), (str), (size), ctx->userdata);   \
            if(ret != 0) {                                                  \
                MD_LOG("Aborted from text() callback.");                    \
                goto abort;                                                 \
            }                                                               \
        }                                                                   \
    } while(0)
```

## 2.11.rtpproxy

callsite:

- `CALL_METHOD(cfsp->bindaddrs_cf, host2, bh[i], AF_INET, AI_PASSIVE, &errmsg)`

- `RTPP_LOG(cmd->glog, RTPP_LOG_ERR, "DELETE: unknown command modifier %c'", *cp); reply_error(cmd, ECODE_PARSE_4)`

- `CALL_SMETHOD(sobj, getidxbyname, "ncmds_rcvd")`

macro:

```cpp
#define CALL_METHOD(obj, method, args...) (obj)->method(obj, ## args)

#define CALL_SMETHOD(obj, method, args...) GET_SMETHODS(obj)->method(obj, ## args)

#define RTPP_LOG(log, args...) CALL_METHOD((log), genwrite, __FUNCTION__, \
  __LINE__, ## args)
```

## 2.12.oniguruma

callsite:

- `ONIGENC_MBC_TO_CODE(enc, p, end)`

- `enclen(enc, p)`

- `IS_SYNTAX_OP(syn, ONIG_SYN_OP_POSIX_BRACKET)`

macro:

```cpp
#define ONIGENC_MBC_TO_CODE(enc,p,end)         (enc)->mbc_to_code((p),(end))

#define enclen(enc,p)          ONIGENC_MBC_ENC_LEN(enc,p)

#define ONIGENC_MBC_ENC_LEN(enc,p)             (enc)->mbc_enc_len(p)

#define IS_SYNTAX_OP(syn, opm)    (((syn)->op  & (opm)) != 0)
```

## 2.13.libjpeg-turbo

callsite:

- `ERREXIT1(cinfo, JERR_NO_QUANT_TABLE, qtblno)`

- `INPUT_BYTE(cinfo, cinfo->data_precision, return FALSE)`

- `TRACEMS4(cinfo, 1, JTRC_SOF, cinfo->unread_marker, (int)cinfo->image_width, (int)cinfo->image_height, cinfo->num_components)`

- `WARNMS2(cinfo, JWRN_EXTRANEOUS_DATA, cinfo->marker->discarded_bytes, c)`

macro:

```cpp
#define ERREXIT1(cinfo, code, p1) \
  ((cinfo)->err->msg_code = (code), \
   (cinfo)->err->msg_parm.i[0] = (p1), \
   (*(cinfo)->err->error_exit) ((j_common_ptr)(cinfo)))

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
            
#define TRACEMS4(cinfo, lvl, code, p1, p2, p3, p4) \
  MAKESTMT(int *_mp = (cinfo)->err->msg_parm.i; \
           _mp[0] = (p1);  _mp[1] = (p2);  _mp[2] = (p3);  _mp[3] = (p4); \
           (cinfo)->err->msg_code = (code); \
           (*(cinfo)->err->emit_message) ((j_common_ptr)(cinfo), (lvl)); )
           
           
#define WARNMS2(cinfo, code, p1, p2) \
  ((cinfo)->err->msg_code = (code), \
   (cinfo)->err->msg_parm.i[0] = (p1), \
   (cinfo)->err->msg_parm.i[1] = (p2), \
   (*(cinfo)->err->emit_message) ((j_common_ptr)(cinfo), -1))
```


# 3.callsite占比


| project | flta | mlta | kelp |
| ---- | ---- | ---- | ---- |
| bind9 | 20 | 24 | 1 |
| bluez | 0 | 0 | 4 |
| cairo | 30 | 9 | 2 |
| cyclonedds | 24 | 19 | 4 |
| dovecot | 15 | 24 | 0 |
| fwupd | 28 | 0 | 3 |
| gdbm | 2 | 10 | 6 |
| gdk-pixbuf | 2 | 1 | 0 |
| hdf5 | 5 | 80 | 4 |
| igraph | 2 | 4 | 0 |
| krb5 | 9 | 1 | 0 |
| libdwarf | 1 | 11 | 5 |
| libjpeg-turbo | 127 | 78 | 0 |
| libpg_query | 4 | 7 | 0 |
| librabbitmq | 0 | 6 | 0 |
| libsndfile | 3 | 5 | 0 |
| libssh | 1 | 12 | 1 |
| lua | 0 | 2 | 0 |
| lxc | 5 | 2 | 0 |
| md4c | 1 | 2 | 3 |
| mdbtools | 0 | 1 | 1 |
| nginx | 3 | 20 | 0 |
| oniguruma | 16 | 2 | 0 |
| opensips | 7 | 1 | 0 |
| pjsip | 13 | 8 | 1 |
| postfix | 1 | 2 | 0 |
| rtpproxy | 4 | 3 | 1 |
| selinux | 11 | 0 | 10 |
| sudo | 49 | 14 | 32 |
| tmux | 1 | 7 | 3 |
| vlc | 16 | 9 | 2 |
| total | 391 | 373 | 84 |