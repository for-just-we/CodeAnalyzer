# 1.Experiment Results

project添加了3个flag，分别表示：

- `only_compiled`: 设置为1表示evaluate的时候只考虑编译过的function

- `only_refered`: 设置为1表示evaluate的时候只考虑address-taken function，设置这个主要是考虑source code层面address-taken function的分析可能会存在偏差，导致漏分析。

- `hard_match`: 设置为0表示做签名匹配的时候只考虑参数数量，设置为1为在此基础上简单的考虑结构体和枚举类型名的匹配，设置这个主要是考虑到C语言中各种显式/隐式类型转换给签名匹配造成的影响。

project一栏的类型为 `{project_name}-{only_compiled}{only_refered}{hard_match}`

## step1

| Project  | Precision(%) | Recall(%) | F1(%) |
|----|----| ---- | ---- |
| nginx-00 | 1.2 | 100.0 | 2.4 |
| nginx-01 | 3.7 | 100.0 | 7.0 |
| nginx-10 | 2.1 | 100.0 | 4.1 |
| nginx-11 | 5.1 | 100.0 | 9.4 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| bind9-00 | 0.2 | 87.0 | 0.3 |
| bind9-01 | 0.4 | 87.0 | 0.7 |
| bind9-10 | 0.7 | 87.0 | 1.3 |
| bind9-11 | 0.9 | 87.0 | 1.8 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| cyclonedds-00 | 0.2 | 98.9 | 0.5 |
| cyclonedds-01 | 0.6 | 98.9 | 1.0 |
| cyclonedds-10 | 1.0 | 98.8 | 1.8 |
| cyclonedds-11 | 2.1 | 98.8 | 3.2 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| dovecot-00 | 0.0 | 100.0 | 0.1 |
| dovecot-01 | 0.1 | 92.5 | 0.2 |
| dovecot-10 | 0.1 | 100.0 | 0.2 |
| dovecot-11 | 0.3 | 92.5 | 0.6 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| hdf5-00 | 0.4 | 96.4 | 0.7 |
| hdf5-01 | 0.5 | 94.3 | 0.8 |
| hdf5-10 | 1.1 | 90.0 | 1.8 |
| hdf5-11 | 1.1 | 89.0 | 1.8 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| igraph-00 | 0.1 | 36.5 | 0.2 |
| igraph-01 | 0.1 | 36.5 | 0.2 |
| igraph-10 | 1.0 | 36.5 | 1.8 |
| igraph-11 | 1.1 | 36.5 | 2.0 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| libdwarf-00 | 0.1 | 100.0 | 0.3 |
| libdwarf-01 | 0.1 | 100.0 | 0.3 |
| libdwarf-10 | 0.8 | 100.0 | 1.4 |
| libdwarf-11 | 0.8 | 100.0 | 1.4 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| lxc-00 | 9.0 | 85.7 | 14.2 |
| lxc-01 | 9.1 | 85.7 | 14.3 |
| lxc-10 | 15.9 | 85.7 | 22.1 |
| lxc-11 | 16.1 | 85.7 | 22.6 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| md4c-00 | 1.0 | 97.4 | 2.0 |
| md4c-01 | 1.2 | 97.4 | 2.4 |
| md4c-10 | 6.7 | 97.4 | 8.0 |
| md4c-11 | 6.7 | 97.4 | 8.0 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| pjsip-00 | 0.1 | 95.3 | 0.1 |
| pjsip-01 | 0.1 | 90.7 | 0.2 |
| pjsip-10 | 0.3 | 95.3 | 0.6 |
| pjsip-11 | 0.7 | 90.7 | 1.2 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| rtpproxy-00 | 0.1 | 96.9 | 0.1 |
| rtpproxy-01 | 0.1 | 96.9 | 0.1 |
| rtpproxy-10 | 0.1 | 96.9 | 0.2 |
| rtpproxy-11 | 0.1 | 96.9 | 0.2 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| selinux-00 | 0.6 | 100.0 | 1.2 |
| selinux-01 | 1.1 | 100.0 | 2.2 |
| selinux-10 | 2.3 | 100.0 | 4.3 |
| selinux-11 | 3.5 | 100.0 | 6.5 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| sudo-00 | 0.3 | 95.7 | 0.7 |
| sudo-01 | 0.4 | 95.7 | 0.7 |
| sudo-10 | 0.5 | 94.6 | 1.0 |
| sudo-11 | 0.6 | 94.6 | 1.1 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| tmux-00 | 2.2 | 100.0 | 3.7 |
| tmux-01 | 6.1 | 100.0 | 8.7 |
| tmux-10 | 6.0 | 100.0 | 8.4 |
| tmux-11 | 13.4 | 100.0 | 17.9 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| vlc-00 | 0.0 | 2.4 | 0.0 |
| vlc-01 | 0.0 | 2.4 | 0.0 |
| vlc-10 | 0.0 | 2.1 | 0.0 |
| vlc-11 | 0.0 | 2.1 | 0.0 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| libjpeg-turbo-00 | 0.5 | 87.7 | 1.0 |
| libjpeg-turbo-01 | 0.6 | 87.7 | 1.2 |
| libjpeg-turbo-10 | 1.1 | 87.7 | 2.1 |
| libjpeg-turbo-11 | 1.6 | 87.7 | 2.9 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| bluez-00 | 0.0 | 100.0 | 0.1 |
| bluez-01 | 0.0 | 100.0 | 0.1 |
| bluez-10 | 0.1 | 100.0 | 0.1 |
| bluez-11 | 0.1 | 100.0 | 0.1 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| gdbm-00 | 1.8 | 100.0 | 3.4 |
| gdbm-01 | 2.2 | 100.0 | 4.3 |
| gdbm-10 | 5.1 | 100.0 | 9.2 |
| gdbm-11 | 7.9 | 100.0 | 13.4 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| cairo-00 | 0.1 | 100.0 | 0.2 |
| cairo-01 | 0.1 | 100.0 | 0.3 |
| cairo-10 | 0.2 | 100.0 | 0.5 |
| cairo-11 | 0.3 | 100.0 | 0.5 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| fwupd-00 | 0.6 | 90.3 | 1.1 |
| fwupd-01 | 0.6 | 90.3 | 1.1 |
| fwupd-10 | 1.6 | 90.3 | 2.8 |
| fwupd-11 | 1.6 | 90.3 | 2.8 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| gdk-pixbuf-00 | 0.2 | 33.3 | 0.3 |
| gdk-pixbuf-01 | 0.2 | 33.3 | 0.3 |
| gdk-pixbuf-10 | 0.7 | 33.3 | 1.4 |
| gdk-pixbuf-11 | 0.7 | 33.3 | 1.4 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| libbpf-00 | 0.5 | 100.0 | 1.0 |
| libbpf-01 | 0.5 | 100.0 | 1.0 |
| libbpf-10 | 3.7 | 100.0 | 7.1 |
| libbpf-11 | 3.7 | 100.0 | 7.1 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| libfuse-00 | 0.4 | 100.0 | 0.8 |
| libfuse-01 | 0.4 | 100.0 | 0.8 |
| libfuse-10 | 0.6 | 100.0 | 1.2 |
| libfuse-11 | 0.6 | 100.0 | 1.2 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| libpg_query-00 | 0.1 | 100.0 | 0.1 |
| libpg_query-01 | 0.1 | 100.0 | 0.3 |
| libpg_query-10 | 0.7 | 100.0 | 1.4 |
| libpg_query-11 | 0.8 | 100.0 | 1.5 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| krb5-00 | 0.2 | 44.4 | 0.4 |
| krb5-01 | 0.2 | 44.4 | 0.4 |
| krb5-10 | 0.6 | 44.4 | 1.2 |
| krb5-11 | 0.6 | 44.4 | 1.2 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| libsndfile-00 | 0.4 | 100.0 | 0.8 |
| libsndfile-01 | 0.4 | 100.0 | 0.9 |
| libsndfile-10 | 1.5 | 100.0 | 2.8 |
| libsndfile-11 | 1.5 | 100.0 | 2.8 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| libucl-00 | 0.6 | 66.7 | 1.1 |
| libucl-01 | 0.7 | 66.7 | 1.4 |
| libucl-10 | 0.0 | 0.0 | 0.0 |
| libucl-11 | 0.0 | 0.0 | 0.0 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| libssh-00 | 0.2 | 86.7 | 0.5 |
| libssh-01 | 0.4 | 86.7 | 0.8 |
| libssh-10 | 1.3 | 86.7 | 2.6 |
| libssh-11 | 1.7 | 86.7 | 3.3 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| mdbtools-00 | 1.0 | 100.0 | 2.0 |
| mdbtools-01 | 1.0 | 100.0 | 2.0 |
| mdbtools-10 | 11.6 | 100.0 | 19.7 |
| mdbtools-11 | 11.6 | 100.0 | 19.7 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| oniguruma-00 | 0.4 | 65.7 | 0.7 |
| oniguruma-01 | 0.3 | 64.9 | 0.6 |
| oniguruma-10 | 0.5 | 65.7 | 0.9 |
| oniguruma-11 | 0.4 | 64.9 | 0.7 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| lua-00 | 0.3 | 100.0 | 0.6 |
| lua-01 | 0.3 | 100.0 | 0.6 |
| lua-10 | 4.1 | 100.0 | 7.1 |
| lua-11 | 4.1 | 100.0 | 7.1 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| open5gs-00 | 0.1 | 100.0 | 0.2 |
| open5gs-01 | 0.3 | 100.0 | 0.5 |
| open5gs-10 | 1.0 | 100.0 | 2.0 |
| open5gs-11 | 1.4 | 100.0 | 2.8 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| opensips-00 | 0.0 | 100.0 | 0.1 |
| opensips-01 | 0.0 | 100.0 | 0.1 |
| opensips-10 | 0.1 | 100.0 | 0.2 |
| opensips-11 | 0.1 | 100.0 | 0.2 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| postfix-00 | 0.2 | 100.0 | 0.3 |
| postfix-01 | 0.2 | 100.0 | 0.4 |
| postfix-10 | 0.6 | 100.0 | 1.2 |
| postfix-11 | 0.8 | 100.0 | 1.6 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| protobuf-c-00 | 2.2 | 100.0 | 4.3 |
| protobuf-c-01 | 2.2 | 100.0 | 4.3 |
| protobuf-c-10 | 16.7 | 100.0 | 28.6 |
| protobuf-c-11 | 16.7 | 100.0 | 28.6 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| librabbitmq-00 | 1.7 | 100.0 | 3.3 |
| librabbitmq-01 | 2.7 | 100.0 | 5.2 |
| librabbitmq-10 | 19.4 | 100.0 | 31.9 |
| librabbitmq-11 | 19.4 | 100.0 | 31.9 |
| <SEP> | <SEP> | <SEP> | <SEP> |


## step2

### codellama-7b-Instruct

| Project  | Precision(%) | Recall(%) | F1(%) |
|----|----| ---- | ---- |
| nginx-00 | 1.7 | 93.5 | 3.2 |
| nginx-01 | 4.9 | 93.5 | 8.9 |
| nginx-10 | 2.8 | 93.5 | 5.3 |
| nginx-11 | 6.5 | 93.5 | 11.7 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| bind9-00 | 0.2 | 85.9 | 0.4 |
| bind9-01 | 0.5 | 85.9 | 1.0 |
| bind9-10 | 0.9 | 85.9 | 1.8 |
| bind9-11 | 1.3 | 85.9 | 2.5 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| cyclonedds-00 | 0.4 | 89.9 | 0.7 |
| cyclonedds-01 | 0.8 | 89.9 | 1.4 |
| cyclonedds-10 | 1.4 | 89.9 | 2.4 |
| cyclonedds-11 | 3.0 | 89.9 | 4.1 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| md4c-00 | 1.2 | 94.9 | 2.4 |
| md4c-01 | 1.4 | 94.9 | 2.7 |
| md4c-10 | 4.5 | 94.9 | 6.1 |
| md4c-11 | 4.5 | 94.9 | 6.1 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| libfuse-00 | 0.6 | 100.0 | 1.1 |
| libfuse-01 | 0.6 | 100.0 | 1.1 |
| libfuse-10 | 0.9 | 100.0 | 1.8 |
| libfuse-11 | 0.9 | 100.0 | 1.8 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| libbpf-00 | 0.7 | 100.0 | 1.3 |
| libbpf-01 | 0.7 | 100.0 | 1.3 |
| libbpf-10 | 5.0 | 100.0 | 9.5 |
| libbpf-11 | 5.0 | 100.0 | 9.5 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| tmux-00 | 3.0 | 99.4 | 4.8 |
| tmux-01 | 7.5 | 99.4 | 10.3 |
| tmux-10 | 7.2 | 99.4 | 9.7 |
| tmux-11 | 15.7 | 99.4 | 20.9 |


### GPT-3.5

| Project  | Precision(%) | Recall(%) | F1(%) |
|----|----| ---- | ---- |
| nginx-00 | 4.7 | 84.5 | 8.6 |
| nginx-01 | 7.3 | 84.5 | 12.8 |
| nginx-10 | 6.2 | 84.5 | 11.0 |
| nginx-11 | 8.8 | 84.5 | 15.3 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| bind9-00 | 0.8 | 83.7 | 1.6 |
| bind9-01 | 1.4 | 83.7 | 2.7 |
| bind9-10 | 2.4 | 83.7 | 4.5 |
| bind9-11 | 2.9 | 83.7 | 5.4 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| tmux-00 | 9.2 | 89.2 | 11.7 |
| tmux-01 | 14.6 | 89.2 | 19.4 |
| tmux-10 | 14.0 | 89.2 | 18.3 |
| tmux-11 | 25.6 | 89.2 | 34.4 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| md4c-00 | 7.0 | 89.7 | 12.7 |
| md4c-01 | 7.4 | 89.7 | 13.2 |
| md4c-10 | 10.5 | 89.7 | 16.0 |
| md4c-11 | 10.5 | 89.7 | 16.0 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| libfuse-00 | 3.3 | 100.0 | 6.5 |
| libfuse-01 | 3.3 | 100.0 | 6.5 |
| libfuse-10 | 4.5 | 100.0 | 8.7 |
| libfuse-11 | 4.5 | 100.0 | 8.7 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| libbpf-00 | 3.2 | 100.0 | 6.2 |
| libbpf-01 | 3.2 | 100.0 | 6.2 |
| libbpf-10 | 25.0 | 100.0 | 40.0 |
| libbpf-11 | 25.0 | 100.0 | 40.0 |



# 2.Experimental Results compare

## 00

| Project | Precision(%) | Recall(%) | F1(%) |
| ---- | ---- | ---- | ---- |
| nginx-origin | 1.2 | 100.0 | 2.4 |
| nginx-codellama-7b-Instruct | 1.7 | 93.5 | 3.2 |
| nginx-gpt-3.5 | 4.7 | 84.5 | 8.6 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| bind9-origin | 0.2 | 87.0 | 0.3 |
| bind9-codellama-7b-Instruct | 0.2 | 85.9 | 0.4 |
| bind9-gpt-3.5 | 0.8 | 83.7 | 1.6 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| tmux-origin | 2.2 | 100.0 | 3.7 |
| tmux-codellama-7b-Instruct | 3.0 | 99.4 | 4.8 |
| tmux-gpt-3.5 | 9.2 | 89.2 | 11.7 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| md4c-00-origin | 1.0 | 97.4 | 2.0 |
| md4c-codellama-7b-Instruct | 1.2 | 94.9 | 2.4 |
| md4c-gpt-3.5 | 7.0 | 89.7 | 12.7 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| libbpf-origin | 0.5 | 100.0 | 1.0 |
| libbpf-codellama-7b-Instruct | 0.7 | 100.0 | 1.3 |
| libbpf-gpt-3.5 | 3.2 | 100.0 | 6.2 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| libfuse-origin | 0.4 | 100.0 | 0.8 |
| libfuse-codellama-7b-Instruct | 0.6 | 100.0 | 1.1 |
| libfuse-gpt-3.5 | 3.3 | 100.0 | 6.5 |