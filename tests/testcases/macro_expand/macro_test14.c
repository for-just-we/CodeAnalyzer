
#define CALL_METHOD(obj, method, args...) (obj)->method(obj, ## args)

#define RTPP_LOG(log, args...) CALL_METHOD((log), genwrite, __FUNCTION__, \
  __LINE__, ## args)

struct ul_opts *
rtpp_command_ul_opts_parse(const struct rtpp_cfg *cfsp, struct rtpp_command *cmd) {
    RTPP_LOG(cmd->glog, RTPP_LOG_ERR, "DELETE: unknown command modifier %c'", *cp);
}