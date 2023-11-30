
size_t const a;
static const size_t b;

typedef ngx_int_t (*ngx_shm_zone_init_pt) (ngx_shm_zone_t *zone, void *data);

typedef size_t ZSTD_sequenceProducer_F (
  void* sequenceProducerState,
  ZSTD_Sequence* outSeqs, size_t outSeqsCapacity,
  const void* src, size_t srcSize,
  const void* dict, size_t dictSize,
  int compressionLevel,
  size_t windowSize
);

// 定义了3种不同的类型，其中2种为指针类型
typedef struct _TRANSMIT_FILE_BUFFERS {
    LPVOID Head;
    DWORD HeadLength;
    LPVOID Tail;
    DWORD TailLength;
} TRANSMIT_FILE_BUFFERS, *PTRANSMIT_FILE_BUFFERS, FAR *LPTRANSMIT_FILE_BUFFERS;

XXH_PUBLIC_API XXH32_hash_t XXH32 (const void* input, size_t len, XXH32_hash_t seed)
{
}

typedef cairo_status_t
(*cairo_spline_add_point_func_t) (void *closure,
				  const cairo_point_t *point,
				  const cairo_slope_t *tangent);


typedef BOOL (* LPFN_TRANSMITPACKETS) (
    SOCKET hSocket,
    TRANSMIT_PACKETS_ELEMENT *lpPacketArray,
    DWORD nElementCount,
    DWORD nSendSize,
    LPOVERLAPPED lpOverlapped,
    DWORD dwFlags
    );

typedef int (*ngx_wsapoll_pt)(
    LPWSAPOLLFD fdArray,
    ULONG fds,
    INT timeout
    );

// 支持可变参数
typedef void (*isc_errorcallback_t)(const char *, int, const char *,
				 const char *, va_list);

typedef ns_hooklist_t ns_hooktable_t[NS_HOOKPOINTS_COUNT];

typedef struct dns_rdata_ #{
	dns_rdatacommon_t common;
	isc_mem_t *mctx; /* if required */
			 /* type & class specific elements */
}
dns_rdata_ #_t;

typedef void timeout_callback_t(void *context);

typedef void iostream_pump_callback_t(enum iostream_pump_status status,
				      void *context);

typedef pam_const void *pam_item_t;