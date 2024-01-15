import os
import yaml
import argparse

from analyzer import ProjectAnalyzer
import logging

def add_subparser(parser: argparse.ArgumentParser):
    parser.add_argument("--temperature", type=float, default=0.4,
                            help="temperature for chatgpt")
    subparsers = parser.add_subparsers(dest='llm')

    gpt_parser = subparsers.add_parser('gpt', help='using OpenAI GPT model')
    gpt_parser.add_argument('--model_type', type=str, choices=['gpt-3.5-turbo', 'gpt-4',
                                                               'gpt-4-1106-preview'])
    gpt_parser.add_argument('--key', type=str, help='api key of openai')

    gemini_parser = subparsers.add_parser('google', help='using Google model')
    gemini_parser.add_argument('--model_type', type=str, choices=['gemini-pro', 'text-bison-001', 'chat-bison-001'],
                            help='model type of gemini, currently only need gemini-pro not gemini-pro-vision,'
                                 'for more details, see: https://github.com/google/generative-ai-docs/blob/main/site/en/tutorials/python_quickstart.ipynb')
    gemini_parser.add_argument('--key', type=str, help='api key of google gemini')

    hf_parser = subparsers.add_parser('hf', help='using model deployed in huggingface')
    hf_parser.add_argument('--address', help='huggingface server ip:port, default to 127.0.0.1:8080',
                           default='127.0.0.1:8080')
    hf_parser.add_argument('--model_name', choices=['codellama', 'wizardcoder'],
                           help='specify model name used. Could be codellama or WizardCoder')
    hf_parser.add_argument('--max_new_tokens', type=int, default=20)

def build_arg_parser():
    parser = argparse.ArgumentParser(description="Command-line tool to analyze projects.")
    parser.add_argument("--pipeline", type=str, choices=['only_type', 'full', 'single', 'single_complex'], default='full',)
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

    parser.add_argument("--load_pre_single_step_analysis_res", action="store_true", default=False,
                        help="If true, will load pre-analyzed single step analyzed result.")
    parser.add_argument("--load_pre_type_analysis_res", action="store_true", default=False,
                        help="If true, will load pre-analyzed type analyzed result.")
    parser.add_argument("--load_pre_semantic_analysis_res", action="store_true", default=False,
                        help="If true, will load pre-analyzed semantic analyzed result.")

    # running epoch用指定epoch轮次GPT的中间log位置，必须在log_llm_output=True或者load_pre_type_analysis_res=True时有效
    parser.add_argument("--running_epoch", type=int, default=1, help="Epoch num for current running,"
                                                                     "used only in experimental setting."
                                                                     "Require --log_llm_output or --load_pre_type_analysis_res option")

    # double_prompt表示是否采用二段式prompt策略
    parser.add_argument("--double_prompt", action="store_true", default=False)
    parser.add_argument("--only_count_scope", action="store_true", default=False, help="only count ground_truth in scope")
    parser.add_argument("--enable_cast", action="store_true", default=False, help="enable cast between param types")

    parser.add_argument("--disable_analysis_for_macro", action="store_true", default=False,
                        help="disable analysis for macro callsite")
    parser.add_argument("--llm_help_cast", action="store_true", default=False, help="enable llm helped type analysis")
    parser.add_argument("--disable_llm_for_uncertain", action="store_true", default=False)
    parser.add_argument("--count_uncertain", action="store_true", default=False,
                        help="enable cast between void* or char* with other pointer type")
    parser.add_argument("--count_cast", action="store_true", default=False,
                        help="enable cast between void* or char* with other pointer type")
    parser.add_argument("--log_res_to_file", action="store_true", default=False,
                        help="If true, will log analysis result to file.")

    # 投票次数
    parser.add_argument("--vote_time", type=int, default=1, help="Vote time for llm.")
    # 评估GPT在传统类型分析无法确定的部分的分析效果
    parser.add_argument("--evaluate_soly_for_llm", action="store_true", default=False,
                        help="If true, the tool will analyze How gpt perform when type analysis cannot determine.")
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
    elif args.llm in {"gpt", "google"}:
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