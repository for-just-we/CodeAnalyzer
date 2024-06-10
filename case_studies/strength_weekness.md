

# 1.The strength of SEA

## 1.1.case1

lxc - src/lxc/confile.c:5473:9

### caller info

The caller is `info.ops->set(info.subkey, value, lxc_conf, info.netdev)`

caller local context is:

```cpp
static int set_config_jump_table_net(const char *key, const char *value,
				     struct lxc_conf *lxc_conf, void *data)
{
	struct config_net_info info = {};
	int ret;
	const char *idxstring;

	idxstring = key + STRLITERALLEN("lxc.net.");
	if (!isdigit(*idxstring))
		return ret_errno(EINVAL);

	if (lxc_config_value_empty(value))
		return clr_config_jump_table_net(key, lxc_conf, data);

	ret = get_network_config_ops(key, lxc_conf, &info, true);
	if (ret)
		return ret;

	return info.ops->set(info.subkey, value, lxc_conf, info.netdev);
}
```

Due to parsing error, the global context for this case is missing. 
The caller summary is:

```
1. The `set_config_jump_table_net` function is designed to handle configuration settings related to network interfaces in a Linux Containers (LXC) environment. It takes a key (representing the network configuration option), a value (the assigned value to that option), a `lxc_conf` structure containing container configuration information, and a `data` pointer. The function parses the key to identify the network interface index, checks if the value is empty, and then retrieves the appropriate network configuration operations structure (`info.ops`). If successful, it calls the `set` function pointer from that structure to apply the configuration setting.

2. The indirect call `info.ops->set(info.subkey, value, lxc_conf, info.netdev)` is the core of the function's functionality. It uses the retrieved network configuration operations to apply the specific configuration setting represented by `value`. The `info.subkey` is the细分 key within the network configuration, `value` is the new value for that setting, `lxc_conf` provides the container's configuration context, and `info.netdev` is likely a pointer to the network device structure. This call delegates the actual configuration update to the appropriate handler based on the network type or operations structure.
```

### true callee info

The true callee context

local:

```cpp
static int set_config_net_ipv6_address(const char *key, const char *value,
				       struct lxc_conf *lxc_conf, void *data)
{
	__do_free char *valdup = NULL;
	__do_free struct lxc_inet6dev *inet6dev = NULL;
	int ret;
	struct lxc_netdev *netdev = data;
	char *slash, *netmask;

	if (!netdev)
		return ret_errno(EINVAL);

	if (lxc_config_value_empty(value))
		return clr_config_net_ipv6_address(key, lxc_conf, data);

	inet6dev = zalloc(sizeof(*inet6dev));
	if (!inet6dev)
		return ret_errno(ENOMEM);

	valdup = strdup(value);
	if (!valdup)
		return ret_errno(ENOMEM);

	inet6dev->prefix = 64;
	slash = strstr(valdup, "/");
	if (slash) {
		*slash = '\0';
		netmask = slash + 1;

		ret = lxc_safe_uint(netmask, &inet6dev->prefix);
		if (ret < 0)
			return ret;
	}

	ret = inet_pton(AF_INET6, valdup, &inet6dev->addr);
	if (!ret || ret < 0)
		return log_error_errno(-EINVAL, EINVAL, "Invalid ipv6 address \"%s\"", valdup);

	list_add_tail(&inet6dev->head, &netdev->ipv6_addresses);
	move_ptr(inet6dev);

	return 0;
}
```

global context:

```cpp
static struct lxc_config_net_t config_jump_table_net[] = {
	/* If a longer key is added please update. */
	#define NETWORK_SUBKEY_SIZE_MAX (STRLITERALLEN("veth.vlan.tagged.id") * 2)
	{ "flags",                  true,  set_config_net_flags,                  get_config_net_flags,                  clr_config_net_flags,                  },
	{ "hwaddr",                 true,  set_config_net_hwaddr,                 get_config_net_hwaddr,                 clr_config_net_hwaddr,                 },
	{ "ipv4.address",           true,  set_config_net_ipv4_address,           get_config_net_ipv4_address,           clr_config_net_ipv4_address,           },
	{ "ipv4.gateway",           true,  set_config_net_ipv4_gateway,           get_config_net_ipv4_gateway,           clr_config_net_ipv4_gateway,           },
	{ "ipv6.address",           true,  set_config_net_ipv6_address,           get_config_net_ipv6_address,           clr_config_net_ipv6_address,           },
	{ "ipv6.gateway",           true,  set_config_net_ipv6_gateway,           get_config_net_ipv6_gateway,           clr_config_net_ipv6_gateway,           },
	{ "link",                   true,  set_config_net_link,                   get_config_net_link,                   clr_config_net_link,                   },
	{ "l2proxy",                true,  set_config_net_l2proxy,                get_config_net_l2proxy,                clr_config_net_l2proxy,                },
	{ "macvlan.mode",           true,  set_config_net_macvlan_mode,           get_config_net_macvlan_mode,           clr_config_net_macvlan_mode,           },
	{ "ipvlan.mode",            true,  set_config_net_ipvlan_mode,            get_config_net_ipvlan_mode,            clr_config_net_ipvlan_mode,            },
	{ "ipvlan.isolation",       true,  set_config_net_ipvlan_isolation,       get_config_net_ipvlan_isolation,       clr_config_net_ipvlan_isolation,       },
	{ "mtu",                    true,  set_config_net_mtu,                    get_config_net_mtu,                    clr_config_net_mtu,                    },
	{ "name",                   true,  set_config_net_name,                   get_config_net_name,                   clr_config_net_name,                   },
	{ "script.down",            true,  set_config_net_script_down,            get_config_net_script_down,            clr_config_net_script_down,            },
	{ "script.up",              true,  set_config_net_script_up,              get_config_net_script_up,              clr_config_net_script_up,              },
	{ "type",                   true,  set_config_net_type,                   get_config_net_type,                   clr_config_net_type,                   },
	{ "vlan.id",                true,  set_config_net_vlan_id,                get_config_net_vlan_id,                clr_config_net_vlan_id,                },
	{ "veth.mode",              true,  set_config_net_veth_mode,              get_config_net_veth_mode,              clr_config_net_veth_mode,              },
	{ "veth.n_rxqueues",        true,  set_config_net_veth_n_rxqueues,        get_config_net_veth_n_rxqueues,        clr_config_net_veth_n_rxqueues,        },
	{ "veth.n_txqueues",        true,  set_config_net_veth_n_txqueues,        get_config_net_veth_n_txqueues,        clr_config_net_veth_n_txqueues,        },
	{ "veth.pair",              true,  set_config_net_veth_pair,              get_config_net_veth_pair,              clr_config_net_veth_pair,              },
	{ "veth.ipv4.route",        true,  set_config_net_veth_ipv4_route,        get_config_net_veth_ipv4_route,        clr_config_net_veth_ipv4_route,        },
	{ "veth.ipv6.route",        true,  set_config_net_veth_ipv6_route,        get_config_net_veth_ipv6_route,        clr_config_net_veth_ipv6_route,        },
	{ "veth.vlan.id",           true,  set_config_net_veth_vlan_id,           get_config_net_veth_vlan_id,           clr_config_net_veth_vlan_id,           },
	{ "veth.vlan.tagged.id",    true,  set_config_net_veth_vlan_tagged_id,    get_config_net_veth_vlan_tagged_id,    clr_config_net_veth_vlan_tagged_id,    },
};
```

where `struct lxc_config_net_t` is lost due to its wrapped by macro.

The callee summary is:

```
local:
The `set_config_net_ipv6_address` function parses and sets an IPv6 address and prefix for a network device in a container configuration, adding the information to the list of IPv6 addresses for the specified network device. It also handles the case of clearing the configuration if the value is empty.

global:
The `set_config_net_ipv6_address` function is used to set the value for the "ipv6.address" configuration option in a struct `lxc_config_net_t` array called `config_jump_table_net`. This function is part of a table of function pointers that handle configuration options for network settings in a Linux Containers (LXC) environment.
```

When matching caller and true-callee. LLM simply response `yes`.

### false callee info


local context:

```cpp
static int set_config_tty_dir(const char *key, const char *value,
			     struct lxc_conf *lxc_conf, void *data)
{
	return set_config_string_item_max(&lxc_conf->ttys.dir, value,
					  NAME_MAX + 1);
}
```

global context

```cpp
The target function set_config_tty_dir is address-taken in a initializer of a variable declaration statement, where the declaree statement is: `static struct lxc_config_t config_jump_table[] `, the initializer is
 ```c
static struct lxc_config_t config_jump_table[] = {
	{ "lxc.arch",                       true,  set_config_personality,                get_config_personality,                clr_config_personality,                },
	{ "lxc.apparmor.profile",           true,  set_config_apparmor_profile,           get_config_apparmor_profile,           clr_config_apparmor_profile,           },
	{ "lxc.apparmor.allow_incomplete",  true,  set_config_apparmor_allow_incomplete,  get_config_apparmor_allow_incomplete,  clr_config_apparmor_allow_incomplete,  },
	{ "lxc.apparmor.allow_nesting",     true,  set_config_apparmor_allow_nesting,     get_config_apparmor_allow_nesting,     clr_config_apparmor_allow_nesting,     },
	{ "lxc.apparmor.raw",               true,  set_config_apparmor_raw,               get_config_apparmor_raw,               clr_config_apparmor_raw,               },
	{ "lxc.autodev.tmpfs.size",         true,  set_config_autodev_tmpfs_size,         get_config_autodev_tmpfs_size,         clr_config_autodev_tmpfs_size,         },
	{ "lxc.autodev",                    true,  set_config_autodev,                    get_config_autodev,                    clr_config_autodev,                    },
	{ "lxc.cap.drop",                   true,  set_config_cap_drop,                   get_config_cap_drop,                   clr_config_cap_drop,                   },
	{ "lxc.cap.keep",                   true,  set_config_cap_keep,                   get_config_cap_keep,                   clr_config_cap_keep,                   },
	{ "lxc.cgroup2",                    false, set_config_cgroup2_controller,         get_config_cgroup2_controller,         clr_config_cgroup2_controller,         },
	{ "lxc.cgroup.dir.monitor.pivot",   true,  set_config_cgroup_monitor_pivot_dir,   get_config_cgroup_monitor_pivot_dir,   clr_config_cgroup_monitor_pivot_dir,   },
	{ "lxc.cgroup.dir.monitor",         true,  set_config_cgroup_monitor_dir,         get_config_cgroup_monitor_dir,         clr_config_cgroup_monitor_dir,         },
	{ "lxc.cgroup.dir.container.inner", true,  set_config_cgroup_container_inner_dir, get_config_cgroup_container_inner_dir, clr_config_cgroup_container_inner_dir, },
	{ "lxc.cgroup.dir.container",       true,  set_config_cgroup_container_dir,       get_config_cgroup_container_dir,       clr_config_cgroup_container_dir,       },
	{ "lxc.cgroup.dir",                 true,  set_config_cgroup_dir,                 get_config_cgroup_dir,                 clr_config_cgroup_dir,                 },
	{ "lxc.cgroup.relative",            true,  set_config_cgroup_relative,            get_config_cgroup_relative,            clr_config_cgroup_relative,            },
	{ "lxc.cgroup",                     false, set_config_cgroup_controller,          get_config_cgroup_controller,          clr_config_cgroup_controller,          },
	{ "lxc.console.buffer.size",        true,  set_config_console_buffer_size,        get_config_console_buffer_size,        clr_config_console_buffer_size,        },
	{ "lxc.console.logfile",            true,  set_config_console_logfile,            get_config_console_logfile,            clr_config_console_logfile,            },
	{ "lxc.console.path",               true,  set_config_console_path,               get_config_console_path,               clr_config_console_path,               },
	{ "lxc.console.rotate",             true,  set_config_console_rotate,             get_config_console_rotate,             clr_config_console_rotate,             },
	{ "lxc.console.size",               true,  set_config_console_size,               get_config_console_size,               clr_config_console_size,               },
	{ "lxc.sched.core",		    true,  set_config_sched_core,		  get_config_sched_core,                 clr_config_sched_core,                 },
	{ "lxc.environment",                true,  set_config_environment,                get_config_environment,                clr_config_environment,                },
	{ "lxc.ephemeral",                  true,  set_config_ephemeral,                  get_config_ephemeral,                  clr_config_ephemeral,                  },
	{ "lxc.execute.cmd",                true,  set_config_execute_cmd,                get_config_execute_cmd,                clr_config_execute_cmd,                },
	{ "lxc.group",                      true,  set_config_group,                      get_config_group,                      clr_config_group,                      },
	{ "lxc.hook.autodev",               true,  set_config_hooks,                      get_config_hooks,                      clr_config_hooks,                      },
	{ "lxc.hook.clone",                 true,  set_config_hooks,                      get_config_hooks,                      clr_config_hooks,                      },
	{ "lxc.hook.destroy",               true,  set_config_hooks,                      get_config_hooks,                      clr_config_hooks,                      },
	{ "lxc.hook.mount",                 true,  set_config_hooks,                      get_config_hooks,                      clr_config_hooks,                      },
	{ "lxc.hook.post-stop",             true,  set_config_hooks,                      get_config_hooks,                      clr_config_hooks,                      },
	{ "lxc.hook.pre-mount",             true,  set_config_hooks,                      get_config_hooks,                      clr_config_hooks,                      },
	{ "lxc.hook.pre-start",             true,  set_config_hooks,                      get_config_hooks,                      clr_config_hooks,                      },
	{ "lxc.hook.start",                 true,  set_config_hooks,                      get_config_hooks,                      clr_config_hooks,                      },
	{ "lxc.hook.start-host",            true,  set_config_hooks,                      get_config_hooks,                      clr_config_hooks,                      },
	{ "lxc.hook.stop",                  true,  set_config_hooks,                      get_config_hooks,                      clr_config_hooks,                      },
	{ "lxc.hook.version",               true,  set_config_hooks_version,              get_config_hooks_version,              clr_config_hooks_version,              },
	{ "lxc.hook",                       true,  set_config_hooks,                      get_config_hooks,                      clr_config_hooks,                      },
	{ "lxc.idmap",                      true,  set_config_idmaps,                     get_config_idmaps,                     clr_config_idmaps,                     },
	{ "lxc.include",                    true,  set_config_includefiles,               get_config_includefiles,               clr_config_includefiles,               },
	{ "lxc.init.cmd",                   true,  set_config_init_cmd,                   get_config_init_cmd,                   clr_config_init_cmd,                   },
	{ "lxc.init.gid",                   true,  set_config_init_gid,                   get_config_init_gid,                   clr_config_init_gid,                   },
	{ "lxc.init.groups",                true,  set_config_init_groups,                get_config_init_groups,                clr_config_init_groups,                },
	{ "lxc.init.uid",                   true,  set_config_init_uid,                   get_config_init_uid,                   clr_config_init_uid,                   },
	{ "lxc.init.cwd",                   true,  set_config_init_cwd,                   get_config_init_cwd,                   clr_config_init_cwd,                   },
	{ "lxc.keyring.session",            true,  set_config_keyring_session,            get_config_keyring_session,            clr_config_keyring_session             },
	{ "lxc.log.file",                   true,  set_config_log_file,                   get_config_log_file,                   clr_config_log_file,                   },
	{ "lxc.log.level",                  true,  set_config_log_level,                  get_config_log_level,                  clr_config_log_level,                  },
	{ "lxc.log.syslog",                 true,  set_config_log_syslog,                 get_config_log_syslog,                 clr_config_log_syslog,                 },
	{ "lxc.monitor.unshare",            true,  set_config_monitor,                    get_config_monitor,                    clr_config_monitor,                    },
	{ "lxc.monitor.signal.pdeath",      true,  set_config_monitor_signal_pdeath,      get_config_monitor_signal_pdeath,      clr_config_monitor_signal_pdeath,      },
	{ "lxc.mount.auto",                 true,  set_config_mount_auto,                 get_config_mount_auto,                 clr_config_mount_auto,                 },
	{ "lxc.mount.entry",                true,  set_config_mount,                      get_config_mount,                      clr_config_mount,                      },
	{ "lxc.mount.fstab",                true,  set_config_mount_fstab,                get_config_mount_fstab,                clr_config_mount_fstab,                },
	{ "lxc.namespace.clone",            true,  set_config_namespace_clone,            get_config_namespace_clone,            clr_config_namespace_clone,            },
	{ "lxc.namespace.keep",             true,  set_config_namespace_keep,             get_config_namespace_keep,             clr_config_namespace_keep,             },
	{ "lxc.namespace.share.",           false, set_config_namespace_share,            get_config_namespace_share,            clr_config_namespace_share,            },
	{ "lxc.time.offset.boot",           true,  set_config_time_offset_boot,           get_config_time_offset_boot,           clr_config_time_offset_boot,           },
	{ "lxc.time.offset.monotonic",      true,  set_config_time_offset_monotonic,      get_config_time_offset_monotonic,      clr_config_time_offset_monotonic,      },
	{ "lxc.net.",                       false, set_config_jump_table_net,             get_config_jump_table_net,             clr_config_jump_table_net,             },
	{ "lxc.net",                        true,  set_config_net,                        get_config_net,                        clr_config_net,                        },
	{ "lxc.no_new_privs",	            true,  set_config_no_new_privs,               get_config_no_new_privs,               clr_config_no_new_privs,               },
	{ "lxc.prlimit",                    false, set_config_prlimit,                    get_config_prlimit,                    clr_config_prlimit,                    },
	{ "lxc.pty.max",                    true,  set_config_pty_max,                    get_config_pty_max,                    clr_config_pty_max,                    },
	{ "lxc.rootfs.managed",             true,  set_config_rootfs_managed,             get_config_rootfs_managed,             clr_config_rootfs_managed,             },
	{ "lxc.rootfs.mount",               true,  set_config_rootfs_mount,               get_config_rootfs_mount,               clr_config_rootfs_mount,               },
	{ "lxc.rootfs.options",             true,  set_config_rootfs_options,             get_config_rootfs_options,             clr_config_rootfs_options,             },
	{ "lxc.rootfs.path",                true,  set_config_rootfs_path,                get_config_rootfs_path,                clr_config_rootfs_path,                },
	{ "lxc.seccomp.allow_nesting",      true,  set_config_seccomp_allow_nesting,      get_config_seccomp_allow_nesting,      clr_config_seccomp_allow_nesting,      },
	{ "lxc.seccomp.notify.cookie",      true,  set_config_seccomp_notify_cookie,      get_config_seccomp_notify_cookie,      clr_config_seccomp_notify_cookie,      },
	{ "lxc.seccomp.notify.proxy",       true,  set_config_seccomp_notify_proxy,       get_config_seccomp_notify_proxy,       clr_config_seccomp_notify_proxy,       },
	{ "lxc.seccomp.profile",            true,  set_config_seccomp_profile,            get_config_seccomp_profile,            clr_config_seccomp_profile,            },
	{ "lxc.selinux.context.keyring",    true,  set_config_selinux_context_keyring,    get_config_selinux_context_keyring,    clr_config_selinux_context_keyring     },
	{ "lxc.selinux.context",            true,  set_config_selinux_context,            get_config_selinux_context,            clr_config_selinux_context,            },
	{ "lxc.signal.halt",                true,  set_config_signal_halt,                get_config_signal_halt,                clr_config_signal_halt,                },
	{ "lxc.signal.reboot",              true,  set_config_signal_reboot,              get_config_signal_reboot,              clr_config_signal_reboot,              },
	{ "lxc.signal.stop",                true,  set_config_signal_stop,                get_config_signal_stop,                clr_config_signal_stop,                },
	{ "lxc.start.auto",                 true,  set_config_start,                      get_config_start,                      clr_config_start,                      },
	{ "lxc.start.delay",                true,  set_config_start,                      get_config_start,                      clr_config_start,                      },
	{ "lxc.start.order",                true,  set_config_start,                      get_config_start,                      clr_config_start,                      },
	{ "lxc.tty.dir",                    true,  set_config_tty_dir,                    get_config_tty_dir,                    clr_config_tty_dir,                    },
	{ "lxc.tty.max",                    true,  set_config_tty_max,                    get_config_tty_max,                    clr_config_tty_max,                    },
	{ "lxc.uts.name",                   true,  set_config_uts_name,                   get_config_uts_name,                   clr_config_uts_name,                   },
	{ "lxc.sysctl",                     false, set_config_sysctl,                     get_config_sysctl,                     clr_config_sysctl,                     },
	{ "lxc.proc",                       false, set_config_proc,                       get_config_proc,                       clr_config_proc,                       },
};
```



We can observe that false callee share similar functionlity with true callee and caller.
But they are used in different scnario.

The analysis for false callee is:

```cpp
Based on the provided summaries, the `set_config_tty_dir` function is responsible for setting the directory for ttys in the LXC configuration, while the indirect call `info.ops->set(info.subkey, value, lxc_conf, info.netdev)` is used to apply a configuration setting related to network interfaces. The indirect call delegates the configuration update to a handler based on the network type or operations structure.

Since `set_config_tty_dir` is specifically for handling TTY device directories and not network configuration, it is unlikely that it would be one of the target functions invoked by the indirect call. Therefore, the answer is 'no'.
```

Where our method successfully identify the false positive.


## 1.2.case2

cairo - src/cairo.c:629:14 

local context:

```cpp
void
cairo_save (cairo_t *cr)
{
    cairo_status_t status;

    if (unlikely (cr->status))
	return;

    status = cr->backend->save (cr);
    if (unlikely (status))
	_cairo_set_error (cr, status);
}
```




summary:


```cpp
1. The `cairo_save` function is responsible for saving the current graphics state in a cairo_t context. It first checks if the context has any errors; if so, it returns immediately. Then, it calls the `save` method of the context's backend, which is responsible for implementing the actual state-saving operation. If the backend operation returns an error, the function sets the error status in the context.

2. The indirect call `cr->backend->save (cr)` is a part of the `cairo_save` function, as it delegates the state-saving operation to the specific backend implementation. This design allows for flexibility and abstraction, ensuring that the backend (such as a PDF renderer, an image surface, or a window system) can handle state saving in a way appropriate for that backend. The function wraps the call with error checking, ensuring that any errors generated by the backend are properly handled.
```


The only true callee info:

local context:

```cpp
static cairo_status_t
_cairo_default_context_save (void *abstract_cr)
{
    cairo_default_context_t *cr = abstract_cr;

    return _cairo_gstate_save (&cr->gstate, &cr->gstate_freelist);
}
```

global context:

 ```c
{
    CAIRO_TYPE_DEFAULT,
    _cairo_default_context_destroy,

    _cairo_default_context_get_original_target,
    _cairo_default_context_get_current_target,

    _cairo_default_context_save,
    _cairo_default_context_restore,

    _cairo_default_context_push_group,
    _cairo_default_context_pop_group,

    _cairo_default_context_set_source_rgba,
    _cairo_default_context_set_source_surface,
    _cairo_default_context_set_source,
    _cairo_default_context_get_source,

    _cairo_default_context_set_antialias,
    _cairo_default_context_set_dash,
    _cairo_default_context_set_fill_rule,
    _cairo_default_context_set_line_cap,
    _cairo_default_context_set_line_join,
    _cairo_default_context_set_line_width,
    _cairo_default_context_set_hairline,
    _cairo_default_context_set_miter_limit,
    _cairo_default_context_set_opacity,
    _cairo_default_context_set_operator,
    _cairo_default_context_set_tolerance,
    _cairo_default_context_get_antialias,
    _cairo_default_context_get_dash,
    _cairo_default_context_get_fill_rule,
    _cairo_default_context_get_line_cap,
    _cairo_default_context_get_line_join,
    _cairo_default_context_get_line_width,
    _cairo_default_context_get_hairline,
    _cairo_default_context_get_miter_limit,
    _cairo_default_context_get_opacity,
    _cairo_default_context_get_operator,
    _cairo_default_context_get_tolerance,

    _cairo_default_context_translate,
    _cairo_default_context_scale,
    _cairo_default_context_rotate,
    _cairo_default_context_transform,
    _cairo_default_context_set_matrix,
    _cairo_default_context_set_identity_matrix,
    _cairo_default_context_get_matrix,

    _cairo_default_context_user_to_device,
    _cairo_default_context_user_to_device_distance,
    _cairo_default_context_device_to_user,
    _cairo_default_context_device_to_user_distance,

    _cairo_default_context_user_to_backend,
    _cairo_default_context_user_to_backend_distance,
    _cairo_default_context_backend_to_user,
    _cairo_default_context_backend_to_user_distance,

    _cairo_default_context_new_path,
    _cairo_default_context_new_sub_path,
    _cairo_default_context_move_to,
    _cairo_default_context_rel_move_to,
    _cairo_default_context_line_to,
    _cairo_default_context_rel_line_to,
    _cairo_default_context_curve_to,
    _cairo_default_context_rel_curve_to,
    NULL, /* arc-to */
    NULL, /* rel-arc-to */
    _cairo_default_context_close_path,
    _cairo_default_context_arc,
    _cairo_default_context_rectangle,
    _cairo_default_context_path_extents,
    _cairo_default_context_has_current_point,
    _cairo_default_context_get_current_point,
    _cairo_default_context_copy_path,
    _cairo_default_context_copy_path_flat,
    _cairo_default_context_append_path,

    NULL, /* stroke-to-path */

    _cairo_default_context_clip,
    _cairo_default_context_clip_preserve,
    _cairo_default_context_in_clip,
    _cairo_default_context_clip_extents,
    _cairo_default_context_reset_clip,
    _cairo_default_context_copy_clip_rectangle_list,

    _cairo_default_context_paint,
    _cairo_default_context_paint_with_alpha,
    _cairo_default_context_mask,

    _cairo_default_context_stroke,
    _cairo_default_context_stroke_preserve,
    _cairo_default_context_in_stroke,
    _cairo_default_context_stroke_extents,

    _cairo_default_context_fill,
    _cairo_default_context_fill_preserve,
    _cairo_default_context_in_fill,
    _cairo_default_context_fill_extents,

    _cairo_default_context_set_font_face,
    _cairo_default_context_get_font_face,
    _cairo_default_context_set_font_size,
    _cairo_default_context_set_font_matrix,
    _cairo_default_context_get_font_matrix,
    _cairo_default_context_set_font_options,
    _cairo_default_context_get_font_options,
    _cairo_default_context_set_scaled_font,
    _cairo_default_context_get_scaled_font,
    _cairo_default_context_font_extents,

    _cairo_default_context_glyphs,
    _cairo_default_context_glyph_path,
    _cairo_default_context_glyph_extents,

    _cairo_default_context_copy_page,
    _cairo_default_context_show_page,

    _cairo_default_context_tag_begin,
    _cairo_default_context_tag_end,
}

struct _cairo_backend {
    cairo_backend_type_t type;
    void (*destroy) (void *cr);

    cairo_surface_t *(*get_original_target) (void *cr);
    cairo_surface_t *(*get_current_target) (void *cr);

    cairo_status_t (*save) (void *cr);
    cairo_status_t (*restore) (void *cr);

    cairo_status_t (*push_group) (void *cr, cairo_content_t content);
    cairo_pattern_t *(*pop_group) (void *cr);

    cairo_status_t (*set_source_rgba) (void *cr, double red, double green, double blue, double alpha);
    cairo_status_t (*set_source_surface) (void *cr, cairo_surface_t *surface, double x, double y);
    cairo_status_t (*set_source) (void *cr, cairo_pattern_t *source);
    cairo_pattern_t *(*get_source) (void *cr);

    cairo_status_t (*set_antialias) (void *cr, cairo_antialias_t antialias);
    cairo_status_t (*set_dash) (void *cr, const double *dashes, int num_dashes, double offset);
    cairo_status_t (*set_fill_rule) (void *cr, cairo_fill_rule_t fill_rule);
    cairo_status_t (*set_line_cap) (void *cr, cairo_line_cap_t line_cap);
    cairo_status_t (*set_line_join) (void *cr, cairo_line_join_t line_join);
    cairo_status_t (*set_line_width) (void *cr, double line_width);
    cairo_status_t (*set_hairline) (void *cr, cairo_bool_t set_hairline);
    cairo_status_t (*set_miter_limit) (void *cr, double limit);
    cairo_status_t (*set_opacity) (void *cr, double opacity);
    cairo_status_t (*set_operator) (void *cr, cairo_operator_t op);
    cairo_status_t (*set_tolerance) (void *cr, double tolerance);

    cairo_antialias_t (*get_antialias) (void *cr);
    void (*get_dash) (void *cr, double *dashes, int *num_dashes, double *offset);
    cairo_fill_rule_t (*get_fill_rule) (void *cr);
    cairo_line_cap_t (*get_line_cap) (void *cr);
    cairo_line_join_t (*get_line_join) (void *cr);
    double (*get_line_width) (void *cr);
    cairo_bool_t (*get_hairline) (void *cr);
    double (*get_miter_limit) (void *cr);
    double (*get_opacity) (void *cr);
    cairo_operator_t (*get_operator) (void *cr);
    double (*get_tolerance) (void *cr);

    cairo_status_t (*translate) (void *cr, double tx, double ty);
    cairo_status_t (*scale) (void *cr, double sx, double sy);
    cairo_status_t (*rotate) (void *cr, double theta);
    cairo_status_t (*transform) (void *cr, const cairo_matrix_t *matrix);
    cairo_status_t (*set_matrix) (void *cr, const cairo_matrix_t *matrix);
    cairo_status_t (*set_identity_matrix) (void *cr);
    void (*get_matrix) (void *cr, cairo_matrix_t *matrix);

    void (*user_to_device) (void *cr, double *x, double *y);
    void (*user_to_device_distance) (void *cr, double *x, double *y);
    void (*device_to_user) (void *cr, double *x, double *y);
    void (*device_to_user_distance) (void *cr, double *x, double *y);

    void (*user_to_backend) (void *cr, double *x, double *y);
    void (*user_to_backend_distance) (void *cr, double *x, double *y);
    void (*backend_to_user) (void *cr, double *x, double *y);
    void (*backend_to_user_distance) (void *cr, double *x, double *y);

    cairo_status_t (*new_path) (void *cr);
    cairo_status_t (*new_sub_path) (void *cr);
    cairo_status_t (*move_to) (void *cr, double x, double y);
    cairo_status_t (*rel_move_to) (void *cr, double dx, double dy);
    cairo_status_t (*line_to) (void *cr, double x, double y);
    cairo_status_t (*rel_line_to) (void *cr, double dx, double dy);
    cairo_status_t (*curve_to) (void *cr, double x1, double y1, double x2, double y2, double x3, double y3);
    cairo_status_t (*rel_curve_to) (void *cr, double dx1, double dy1, double dx2, double dy2, double dx3, double dy3);
    cairo_status_t (*arc_to) (void *cr, double x1, double y1, double x2, double y2, double radius);
    cairo_status_t (*rel_arc_to) (void *cr, double dx1, double dy1, double dx2, double dy2, double radius);
    cairo_status_t (*close_path) (void *cr);

    cairo_status_t (*arc) (void *cr, double xc, double yc, double radius, double angle1, double angle2, cairo_bool_t forward);
    cairo_status_t (*rectangle) (void *cr, double x, double y, double width, double height);

    void (*path_extents) (void *cr, double *x1, double *y1, double *x2, double *y2);
    cairo_bool_t (*has_current_point) (void *cr);
    cairo_bool_t (*get_current_point) (void *cr, double *x, double *y);

    cairo_path_t *(*copy_path) (void *cr);
    cairo_path_t *(*copy_path_flat) (void *cr);
    cairo_status_t (*append_path) (void *cr, const cairo_path_t *path);

    cairo_status_t (*stroke_to_path) (void *cr);

    cairo_status_t (*clip) (void *cr);
    cairo_status_t (*clip_preserve) (void *cr);
    cairo_status_t (*in_clip) (void *cr, double x, double y, cairo_bool_t *inside);
    cairo_status_t (*clip_extents) (void *cr, double *x1, double *y1, double *x2, double *y2);
    cairo_status_t (*reset_clip) (void *cr);
    cairo_rectangle_list_t *(*clip_copy_rectangle_list) (void *cr);

    cairo_status_t (*paint) (void *cr);
    cairo_status_t (*paint_with_alpha) (void *cr, double opacity);
    cairo_status_t (*mask) (void *cr, cairo_pattern_t *pattern);

    cairo_status_t (*stroke) (void *cr);
    cairo_status_t (*stroke_preserve) (void *cr);
    cairo_status_t (*in_stroke) (void *cr, double x, double y, cairo_bool_t *inside);
    cairo_status_t (*stroke_extents) (void *cr, double *x1, double *y1, double *x2, double *y2);

    cairo_status_t (*fill) (void *cr);
    cairo_status_t (*fill_preserve) (void *cr);
    cairo_status_t (*in_fill) (void *cr, double x, double y, cairo_bool_t *inside);
    cairo_status_t (*fill_extents) (void *cr, double *x1, double *y1, double *x2, double *y2);

    cairo_status_t (*set_font_face) (void *cr, cairo_font_face_t *font_face);
    cairo_font_face_t *(*get_font_face) (void *cr);
    cairo_status_t (*set_font_size) (void *cr, double size);
    cairo_status_t (*set_font_matrix) (void *cr, const cairo_matrix_t *matrix);
    void (*get_font_matrix) (void *cr, cairo_matrix_t *matrix);
    cairo_status_t (*set_font_options) (void *cr, const cairo_font_options_t *options);
    void (*get_font_options) (void *cr, cairo_font_options_t *options);
    cairo_status_t (*set_scaled_font) (void *cr, cairo_scaled_font_t *scaled_font);
    cairo_scaled_font_t *(*get_scaled_font) (void *cr);
    cairo_status_t (*font_extents) (void *cr, cairo_font_extents_t *extents);

    cairo_status_t (*glyphs) (void *cr,
			      const cairo_glyph_t *glyphs, int num_glyphs,
			      cairo_glyph_text_info_t *info);
    cairo_status_t (*glyph_path) (void *cr,
				  const cairo_glyph_t *glyphs, int num_glyphs);

    cairo_status_t (*glyph_extents) (void *cr,
				     const cairo_glyph_t *glyphs,
				     int num_glyphs,
				     cairo_text_extents_t *extents);

    cairo_status_t (*copy_page) (void *cr);
    cairo_status_t (*show_page) (void *cr);

    cairo_status_t (*tag_begin) (void *cr, const char *tag_name, const char *attributes);
    cairo_status_t (*tag_end) (void *cr, const char *tag_name);
}
```

LLM's response when matching:

```
Based on the provided functional summaries, the indirect call `cr->backend->save (cr)` in the `cairo_save` function is designed to delegate the state-saving operation to the specific backend implementation. The `_cairo_default_context_save` function, as described, is responsible for saving the state of the default cairo context by calling `_cairo_gstate_save`.

Given that the `save` method in the backend is intended to handle state-saving operations and `_cairo_default_context_save` is one such function that performs this operation, it is plausible that `_cairo_default_context_save` could be a target function that the indirect call potentially invokes. However, this assessment is made under the assumption that the default backend's `save` method is indeed `_cairo_default_context_save`, and the actual invocation would depend on the specific backend implementation and how it is linked or set up in the context.

Therefore, the answer is 'yes', but it is important to note that this is a functional assessment and that additional context, such as the actual implementation, control-flow, and data-flow, would be necessary to confirm the invocation at runtime.
```

For the rest 207 potential callee like: `close_path_dashed`, `_cairo_default_context_get_fill_rule`. SEA simply remove them due to semantic-incompatible and filter the only true callee from 208 targets.




## 1.3.case3

bind9 - lib/dns/rdataset.c:90:3

caller us: 

caller local context:

```mermaid
void
dns__rdataset_disassociate(dns_rdataset_t *rdataset DNS__DB_FLARG) {
	/*
	 * Disassociate 'rdataset' from its rdata, allowing it to be reused.
	 */

	REQUIRE(DNS_RDATASET_VALID(rdataset));
	REQUIRE(rdataset->methods != NULL);

	if (rdataset->methods->disassociate != NULL) {
		(rdataset->methods->disassociate)(rdataset DNS__DB_FLARG_PASS);
	}
	*rdataset = (dns_rdataset_t){
		.magic = DNS_RDATASET_MAGIC,
		.link = ISC_LINK_INITIALIZER,
		.count = DNS_RDATASET_COUNT_UNDEFINED,
	};
}
```

Where baseline analyze 221 callees. 

One of true target is:

```cpp
static void
rdataset_disassociate(dns_rdataset_t *rdataset DNS__DB_FLARG) {
	dns_db_t *db = rdataset->slab.db;
	dns_dbnode_t *node = rdataset->slab.node;

	dns__db_detachnode(db, &node DNS__DB_FLARG_PASS);
}
```

The global context for the true callee is:

 ```c
{
	.disassociate = rdataset_disassociate,
	.first = rdataset_first,
	.next = rdataset_next,
	.current = rdataset_current,
	.clone = rdataset_clone,
	.count = rdataset_count,
	.settrust = rdataset_settrust,
}

struct dns_rdatasetmethods {
	void (*disassociate)(dns_rdataset_t *rdataset DNS__DB_FLARG);
	isc_result_t (*first)(dns_rdataset_t *rdataset);
	isc_result_t (*next)(dns_rdataset_t *rdataset);
	void (*current)(dns_rdataset_t *rdataset, dns_rdata_t *rdata);
	void (*clone)(dns_rdataset_t	    *source,
		      dns_rdataset_t *target DNS__DB_FLARG);
	unsigned int (*count)(dns_rdataset_t *rdataset);
	isc_result_t (*addnoqname)(dns_rdataset_t   *rdataset,
				   const dns_name_t *name);
	isc_result_t (*getnoqname)(dns_rdataset_t *rdataset, dns_name_t *name,
				   dns_rdataset_t	 *neg,
				   dns_rdataset_t *negsig DNS__DB_FLARG);
	isc_result_t (*addclosest)(dns_rdataset_t   *rdataset,
				   const dns_name_t *name);
	isc_result_t (*getclosest)(dns_rdataset_t *rdataset, dns_name_t *name,
				   dns_rdataset_t	 *neg,
				   dns_rdataset_t *negsig DNS__DB_FLARG);
	void (*settrust)(dns_rdataset_t *rdataset, dns_trust_t trust);
	void (*expire)(dns_rdataset_t *rdataset DNS__DB_FLARG);
	void (*clearprefetch)(dns_rdataset_t *rdataset);
	void (*setownercase)(dns_rdataset_t *rdataset, const dns_name_t *name);
	void (*getownercase)(const dns_rdataset_t *rdataset, dns_name_t *name);
	isc_result_t (*addglue)(dns_rdataset_t	*rdataset,
				dns_dbversion_t *version, dns_message_t *msg);
}
```

LLM's summary for callee is:

```
local:
The rdataset_disassociate function detaches the specified DNS rdataset from its associated database node, effectively disassociating the rdataset from the database.

global:
The `rdataset_disassociate` function pointer is part of the `dns_rdatasetmethods_t` structure, which defines a set of operations for managing DNS rdatasets. Its purpose is to dissociate or release a DNS rdataset, as indicated by its assignment to the `disassociate` field in the struct initializer. This function is likely responsible for freeing resources or disconnecting the rdataset from associated data structures.
```

After filtering of SEA, the size of target set is decrease from 221 to 6.



# 2.Potential Threat

vlc - src/modules/modules.c:243:19|

caller is `probe(cb, i < strict_total, ap);`

local context:

```c
module_t *(vlc_module_load)(struct vlc_logger *log, const char *capability,
                            const char *name, bool strict,
                            vlc_activate_t probe, ...)
{
    if (name == NULL || name[0] == '\0')
        name = "any";

    /* Find matching modules */
    module_t **mods;
    size_t strict_total;
    ssize_t total = vlc_module_match(capability, name, strict,
                                     &mods, &strict_total);

    if (unlikely(total < 0))
        return NULL;

    vlc_debug(log, "looking for %s module matching \"%s\": %zd candidates",
              capability, name, total);

    module_t *module = NULL;
    va_list args;

    va_start(args, probe);

    for (size_t i = 0; i < (size_t)total; i++) {
        module_t *cand = mods[i];
        int ret = VLC_EGENERIC;
        void *cb = vlc_module_map(log, cand);

        if (cb != NULL) {
            va_list ap;

            va_copy(ap, args);
            ret = probe(cb, i < strict_total, ap);
            va_end(ap);
        }

        switch (ret) {
            case VLC_SUCCESS:
                vlc_debug(log, "using %s module \"%s\"", capability,
                          module_get_object(cand));
                module = cand;
                /* fall through */
            case VLC_ETIMEOUT:
                goto done;
        }
    }

done:
    va_end (args);

    if (module == NULL)
        vlc_debug(log, "no %s modules matched with name %s", capability, name);

    free(mods);
    return module;
}
```

The caller summary is:

```
The indirect call `probe(cb, i < strict_total, ap)` is used to test each candidate module's suitability. The `cb` argument is a pointer to the module's control function, `i < strict_total` is a boolean indicating whether the current candidate is from the strict match list, and `ap` is a variable argument list. The probe function is called for each module, allowing it to make a decision based on the module's control interface and additional arguments. If the probe returns `VLC_SUCCESS`, the module is selected, and the loop is exited. If it returns `VLC_ETIMEOUT`, the search continues but will stop at the first non-strict match.
```


Where one true callee is:

```cpp
static int generic_start(void *func, bool forced, va_list ap)
{
    vlc_object_t *obj = va_arg(ap, vlc_object_t *);
    int (*activate)(vlc_object_t *) = func;
    int ret;

    obj->force = forced;
    ret = activate(obj);
    if (ret != VLC_SUCCESS)
        vlc_objres_clear(obj);
    return ret;
}
```

The summary is:

```cpp
The generic_start function is a helper function that activates a given function pointer (with a vlc_object_t parameter) while optionally forcing its execution, and it handles error cleanup by resetting the object's state if the activation fails.
```

There is not obvious semantic-relation between caller and callee. Hence, LLM's response is

```
Based on the provided summaries, it seems that the `generic_start` function is not directly related to the functionality of the `probe` function. The `probe` function is used to test the suitability of candidate modules in the `vlc_module_load` function by calling a control function (`cb`) provided by each module. On the other hand, `generic_start` is a helper function that activates a given function pointer and handles error cleanup.

There is no direct indication that the `probe` function would invoke `generic_start` based on the described responsibilities of these functions. Therefore, the answer is 'no'.
```


Thereby in cases where no semantic-relation present, SEA would fail.