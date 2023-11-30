
typedef struct mosquitto_plugin_id_t{
	struct mosquitto__listener *listener;
} mosquitto_plugin_id_t;

typedef struct {
    const void* srcPtr;
    size_t srcSize;
    void*  cPtr;
    size_t cRoom;
    size_t cSize;
    void*  resPtr;
    size_t resSize;
} blockParam_t;

struct Student {
    int num, stunumber, *datas, friend_ids[10];
};