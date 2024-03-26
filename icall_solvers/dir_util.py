import os

def get_parent_directory(file, levels=4):
    path = os.path.realpath(file)
    for _ in range(levels):
        path = os.path.dirname(path)
    return path