
typedef struct mosquitto_plugin_id_t{
	struct mosquitto__listener *listener;
} mosquitto_plugin_id_t;

// typedef中首先定义匿名结构体再定义类型别名
typedef struct {
    const void* srcPtr;
    size_t srcSize;
    void*  cPtr;
    size_t cRoom;
    size_t cSize;
    void*  resPtr;
    size_t resSize;
} blockParam_t;

// 随便构造的，一个field_declaration定义多个field
struct Student {
    int num, stunumber, *datas, friend_ids[10];
};

// 复杂匿名结构体定义+变量声明+初始化，from hdf5
struct {
    herr_t (*func)(void);
    const char *descr;
} initializer[] = {
     {H5E_init, "error"}
    ,{H5VL_init_phase1, "VOL"}
    ,{H5SL_init, "skip lists"}
    ,{H5FD_init, "VFD"}
    ,{H5_default_vfd_init, "default VFD"}
    ,{H5P_init_phase1, "property list"}
    ,{H5AC_init, "metadata caching"}
    ,{H5L_init, "link"}
    ,{H5S_init, "dataspace"}
    ,{H5PL_init, "plugins"}
    /* Finish initializing interfaces that depend on the interfaces above */
    ,{H5P_init_phase2, "property list"}
    ,{H5VL_init_phase2, "VOL"}
    };


typedef struct H5FS_section_class_t {
    /* Class variables */
    const unsigned type;        /* Type of free space section */
    size_t         serial_size; /* Size of serialized form of section */
    unsigned       flags;       /* Class flags */
    void          *cls_private; /* Class private information */

    /* Class methods */
    herr_t (*init_cls)(struct H5FS_section_class_t *,
                       void *);                        /* Routine to initialize class-specific settings */
    herr_t (*term_cls)(struct H5FS_section_class_t *); /* Routine to terminate class-specific settings */

    /* Object methods */
    herr_t (*add)(H5FS_section_info_t **, unsigned *,
                  void *); /* Routine called when section is about to be added to manager */
    herr_t (*serialize)(const struct H5FS_section_class_t *, const H5FS_section_info_t *,
                        uint8_t *); /* Routine to serialize a "live" section into a buffer */
    H5FS_section_info_t *(*deserialize)(
        const struct H5FS_section_class_t *, const uint8_t *, haddr_t, hsize_t,
        unsigned *); /* Routine to deserialize a buffer into a "live" section */
    htri_t (*can_merge)(const H5FS_section_info_t *, const H5FS_section_info_t *,
                        void *); /* Routine to determine if two nodes are mergeable */
    herr_t (*merge)(H5FS_section_info_t **, H5FS_section_info_t *, void *); /* Routine to merge two nodes */
    htri_t (*can_shrink)(const H5FS_section_info_t *,
                         void *);                     /* Routine to determine if node can shrink container */
    herr_t (*shrink)(H5FS_section_info_t **, void *); /* Routine to shrink container */
    herr_t (*free)(H5FS_section_info_t *);            /* Routine to free node */
    herr_t (*valid)(const struct H5FS_section_class_t *,
                    const H5FS_section_info_t *); /* Routine to check if a section is valid */
    H5FS_section_info_t *(*split)(H5FS_section_info_t *, hsize_t); /* Routine to create the split section */
    herr_t (*debug)(const H5FS_section_info_t *, FILE *, int,
                    int); /* Routine to dump debugging information about a section */
} H5FS_section_class_t;