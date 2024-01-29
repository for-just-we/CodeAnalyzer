
#define sudo_debug_exit_bool(_func, _file, _line, _sys, _ret)		       \
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


struct sudo_defs_types {
    const char *name;
    int type;
    const char *desc;
    struct def_values *values;
    bool (*callback)(struct sudoers_context *ctx, const char *file, int line, int column, const union sudo_defs_val *, int op);
    union sudo_defs_val sd_un;
};


static bool
run_callback(struct sudoers_context *ctx, const char *file, int line,
    int column, struct sudo_defs_types *def, int op)
{
    debug_decl(run_callback, SUDOERS_DEBUG_DEFAULTS);

    if (def->callback == NULL)
	debug_return_bool(true);
    debug_return_bool(def->callback(ctx, file, line, column, &def->sd_un, op));
}