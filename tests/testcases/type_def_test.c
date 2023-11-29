
size_t const a;
static const size_t b;

typedef size_t ZSTD_sequenceProducer_F (
  void* sequenceProducerState,
  ZSTD_Sequence* outSeqs, size_t outSeqsCapacity,
  const void* src, size_t srcSize,
  const void* dict, size_t dictSize,
  int compressionLevel,
  size_t windowSize
);

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