from tree_sitter import Language, Parser
import platform
import os

system_name = platform.system()
root_path = os.path.dirname(os.path.dirname(__file__))
# set path to tree-sitter dynamic lib
# linux
if system_name == 'Linux':
    libpath = f"{root_path}/resources/my-languages.so"
# macos
elif system_name == 'Darwin':
    libpath = f"{root_path}/resources/my-languages.dylib"
# windows
elif system_name == 'Windows':
    libpath = f"{root_path}/resources/my-languages.dll"
else:
    raise RuntimeError("unsupported system: ", system_name)

language = Language(libpath, "c")
parser = Parser()
parser.set_language(language)