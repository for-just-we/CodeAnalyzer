import os
import yaml
import argparse

from analyzer import ProjectAnalyzer
import logging

def add_subparser(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers(dest='llm')

    gpt_parser = subparsers.add_parser('gpt', help='using OpenAI GPT model')
    gpt_parser.add_argument('--model_type', type=str, choices=['gpt-3.5-turbo', 'gpt-4'])
    gpt_parser.add_argument('--key', type=str, help='api key of openai')

    hf_parser = subparsers.add_parser('hf', help='using model deployed in huggingface')
    hf_parser.add_argument('--ip', help='huggingface server ip, default to 127.0.0.1',
                           default='127.0.0.1')
    hf_parser.add_argument('--port', help='server port, default to 8888',
                           default=8888)
    hf_parser.add_argument('--model_name', help='specify model name used. Could be codellama or llama2')

def build_arg_parser():
    parser = argparse.ArgumentParser(description="Command-line tool to analyze projects.")
    parser.add_argument("--debug", action="store_true", default=False,
                        help="If true, set to debug mode")
    parser.add_argument("--log_llm_output", action="store_true", default=False,
                        help="If true, log llm output to log file")
    # 添加--project参数，并设置nargs='+'，以接受一个或多个值
    parser.add_argument("--projects", nargs='+', help="One or more projects to analyze")
    parser.add_argument("--scope_strategy", type=str, choices=['no', 'base'], default='base',
                        help='scope strategy to use')
    parser.add_argument("--max_try_time", type=int, default=3, help="max trying time for one llm query")
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

    if args.llm == "hf":
        model_name = args.model_name
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
                                           project, model_name)
        project_analyzer.evaluate()

if __name__ == '__main__':
    main()