from typing import List, Set

if __name__ == '__main__':
    # file_path = "/Users/prophe/Workspace/projects/experiments" \
    #             "/benchmarks/potentialTargets/cairo-1.16/objs/icall_info.txt"
    # lines: List[str] = open(file_path, 'r', encoding='utf-8').readlines()
    # lines = [line.strip() for line in lines]
    # visited_line: Set[str] = set()
    # for line in lines:
    #     res: List[str] = line.split("/")
    #     idx = 0
    #     while res[idx] == "..":
    #         idx += 1
    #     new_line = "/".join(res[idx: ])
    #     if not new_line in visited_line:
    #         print(new_line)
    #         visited_line.add(new_line)
    import platform
    print(platform.system())