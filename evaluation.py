import os
import yaml
import argparse

from tool import ProjectAnalyzer
import logging

def add_subparser(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers(dest='llm')
    parser.add_argument('--func_num_per_batch', type=int, default=10)
    parser.add_argument('--batch_size', type=int, default=1)

    gpt_parser = subparsers.add_parser('gpt', help='using OpenAI GPT model')
    gpt_parser.add_argument('--model_type', type=str, choices=['gpt-3.5-turbo', 'gpt-4'])
    gpt_parser.add_argument('--key', type=str, help='api key of openai')

    hf_parser = subparsers.add_parser('hf', help='using model deployed in huggingface')
    hf_parser.add_argument('--ip', help='huggingface server ip, default to 127.0.0.1',
                           default='127.0.0.1')
    hf_parser.add_argument('--port', help='server port, default to 8888',
                           default=8888)

def build_arg_parser():
    parser = argparse.ArgumentParser(description="Command-line tool to analyze projects.")
    parser.add_argument("--stage", type=int, choices=[1, 2], help='analyzing state, 1->only run signature match,'
                                                                  '2 -> run signature match first then use LLM to simply filter with function declarator.',
                        default=1)

    # evaluate的时候只考虑compile中的函数还是考虑所有的函数
    parser.add_argument("--only_compiled", action="store_true", default=False,
                        help='only consider compiled functions or all functions in a project.')
    # evaluate的时候是否只考虑address function，设置这个选项是因为考虑到source code下分析address function比IR层面难度大些。
    # 除了动态加载函数外还有parser的解析错误情况
    parser.add_argument("--only_refered", action="store_true", default=False,
                        help="only consider successfully analyzed address-taken function. It should be note that in source"
                             " code level address-taken function analyzing may not be as precise as in IR-level."
                             " Considering parsing error of syntax parser. As well as dynamically loaded functions.")
    # 类型匹配的时候是否采用hard match
    parser.add_argument("--hard_match", action="store_true", default=False,
                        help="If hard match is false, then when matching signatures. We only compare the argument num and parameter num."
                             "It set to true, we implement a simple strategy to compare the type of the parameters."
                             "This is considered due to explicit/implicit cast operations in C/C++ programs.")
    parser.add_argument("--debug", action="store_true", default=False,
                        help="If true, set to debug mode")


    parser.add_argument("--log_llm_output", action="store_true", default=False,
                        help="If true, log llm output to log file")
    parser.add_argument("--run_all_groups", action="store_true", default=False,
                        help="run eight groups, ignore previous only_compiled, only_refered, hard_match functions")
    # 添加--project参数，并设置nargs='+'，以接受一个或多个值
    parser.add_argument("--projects", nargs='+', help="One or more projects to analyze")
    parser.add_argument("--scope_strategy", type=str, choices=['no', 'base'], default='base',
                        help='scope strategy to use')
    parser.add_argument("--max_try_time", type=int, default=5, help="max trying time for one llm query")
    parser.add_argument("--num_worker", type=int, default=10, help="num worker used in sending request to llm")
    add_subparser(parser)
    return parser

def main():
    config_data: dict = yaml.safe_load(open("config.yaml", 'r', encoding='utf-8'))
    root_path: str = config_data['root']
    parser = build_arg_parser()
    args = parser.parse_args()
    # 检查是否提供了项目参数
    if not args.projects:
        parser.error("You must specify one or more project to analyze")

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.run_all_groups:
        groups = [(False,False), (False,True), (True,False), (True,True)]
    else:
        groups = [(args.only_refered, args.hard_match)]

    if args.llm == "codellama":
        model_name = f"codellama-{args.model_type}"
    elif args.llm == "gpt":
        model_name = args.model_type
    else:
        model_name = ""

    # 打印项目参数的值
    for project in args.projects:
        logging.info(f"analyzing project: {project}")
        project_included_func_file = os.path.join(root_path, "infos", "funcs", f"{project}.txt")
        icall_infos_file = os.path.join(root_path, "infos", "icall_infos", f"{project}.txt")
        project_root = os.path.join(root_path, "projects", project)
        project_analyzer = ProjectAnalyzer(project_included_func_file, icall_infos_file, project_root, args,
                                            project, groups, model_name)
        project_analyzer.evaluate()


if __name__ == '__main__':
    main()