

typedef enum {
    CAIRO_BOILERPLATE_MODE_TEST,
    CAIRO_BOILERPLATE_MODE_PERF,

    /* This will allow running performance test with threads. The
     * GL backend is very slow on some drivers when run with thread
     * awareness turned on. */
    CAIRO_BOILERPLATE_MODE_PERF_THREADS,
} cairo_boilerplate_mode_t;


typedef enum _cairo_backend_type {
    CAIRO_TYPE_DEFAULT,
    CAIRO_TYPE_SKIA,
} cairo_backend_type_t;

enum Status {
    ABNORMAL,
    NORMAL
};

enum {
    CAIRO_BOILERPLATE_MODE_TEST,
    CAIRO_BOILERPLATE_MODE_PERF,

    /* This will allow running performance test with threads. The
     * GL backend is very slow on some drivers when run with thread
     * awareness turned on. */
    CAIRO_BOILERPLATE_MODE_PERF_THREADS,
} cairo_boilerplate_mode_t;