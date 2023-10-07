from typing import Tuple

def loc_inside(loc: Tuple[int, int], start_loc: Tuple[int, int],
               end_loc: Tuple[int, int]) -> bool:
    # 如果区间在同一行
    if start_loc[0] == end_loc[0]:
        if loc[0] == start_loc[0]:
            return start_loc[1] <= loc[1] <= end_loc[1]
        else:
            return False
    # 如果区间在不同行，判断给定位置是否在区间内
    elif start_loc[0] < end_loc[0]:
        if start_loc[0] == loc[0]:
            return start_loc[1] <= loc[1]
        elif loc[0] == end_loc[0]:
            return loc[1] <= end_loc[1]
        elif start_loc[0] < loc[0] < end_loc[0]:
            return True

    return False