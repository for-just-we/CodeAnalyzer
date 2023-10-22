
# 二分类

不考虑refered，采用simple match

| project | precision | recall | F1 |
| ---- | ---- | ---- | ---- |
| nginx | 2.1 | 100.0 | 4.1 |
| tmux | 1.2 | 100.0 | 2.4 |
| libssh | 0.4 | 100.0 | 0.7 |
| gdbm | 5.6 | 100.0 | 10.5 |

# indirect-call匹配

| project | precision | recall | F1 |
| ---- | ---- | ---- | ---- |
| nginx | 3.0 | 84.2 | 5.6 |
| tmux | 2.3 | 100.0 | 3.8 |
| libssh | 0.4 | 86.7 | 0.8 |
| gdbm | 3.1 | 79.8 | 5.8 |

# 其它类别

| project-binary | precision | recall | F1 |
| ---- | ---- | ---- | ---- |
| nginx-01 | 4.3 | 100.0 | 8.2 |
| nginx-10 | 6.7 | 100.0 | 12.5 |
| nginx-11 | 10.0 | 100.0 | 18.2 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| tmux-01 | 5.7 | 100.0 | 10.9 |
| tmux-10 | 3.2 | 100.0 | 6.2 |
| tmux-11 | 21.3 | 100.0 | 35.1 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| libssh-01 | 0.4 | 100.0 | 0.7 |
| libssh-10 | 4.2 | 100.0 | 8.0 |
| libssh-11 | 4.2 | 100.0 | 8.0 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| gdbm-01 | 5.6 | 100.0 | 10.5 |
| gdbm-10 | 10.3 | 100.0 | 18.6 |
| gdbm-11 | 10.3 | 100.0 | 18.6 |


| project | precision | recall | F1 |
| ---- | ---- | ---- | ---- |
| nginx-01 | 8.0 | 84.2 | 13.7 |
| nginx-10 | 6.3 | 84.2 | 10.3 |
| nginx-11 | 11.1 | 84.2 | 17.6 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| tmux-01 | 6.4 | 100.0 | 9.1 |
| tmux-10 | 6.0 | 100.0 | 8.4 |
| tmux-11 | 13.4 | 100.0 | 17.9 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| libssh-01 | 0.7 | 86.7 | 1.5 |
| libssh-10 | 7.1 | 86.7 | 11.5 |
| libssh-11 | 8.3 | 86.7 | 13.6 |
| <SEP> | <SEP> | <SEP> | <SEP> |
| gdbm-01 | 4.9 | 79.8 | 8.7 |
| gdbm-10 | 8.6 | 79.8 | 14.4 |
| gdbm-11 | 12.8 | 79.8 | 20.3 |