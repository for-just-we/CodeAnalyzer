import os
import platform
from tree_sitter import Language

def main():
    system_name = platform.system()
    if system_name == 'Linux':
        file_name = "my-languages.so"
    # macos
    elif system_name == 'Darwin':
        file_name = "my-languages.dylib"
    # windows
    elif system_name == 'Windows':
        file_name = "my-languages.dll"
    else:
        raise RuntimeError("unsupported system: ", system_name)

    if not (os.path.exists('tree-sitter-c') and os.path.exists('tree-sitter-cpp')):
        raise RuntimeError("please download tree-sitter-c and tree-sitter-cpp from github first")

    Language.build_library(
        # Store the library in the `build` directory
        file_name,
        # Include one or more languages
        [
            'tree-sitter-c',
            'tree-sitter-cpp'
        ]
    )

# Before run this script, please download tree-sitter-c and tree-sitter-cpp from https://github.com/tree-sitter/tree-sitter-c and https://github.com/tree-sitter/tree-sitter-cpp
# You can run git clone from `<project_root>/resources` dir or download zip and unzip to resources dir.
if __name__ == '__main__':
    main()