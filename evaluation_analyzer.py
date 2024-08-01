import os
import argparse

from typing import List, Set
from analyzer import ProjectAnalyzer
import logging
from config import supported_model_list, suffix

mapping = {
    "sea": "addr_site_v2",
    "single": "single_step"
}

def add_subparser(parser: argparse.ArgumentParser):
    parser.add_argument("--temperature", type=float, default=1,
                            help="temperature for llm")
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

    zhipu_parser = subparsers.add_parser('zhipu', help='using zhipu model')
    zhipu_parser.add_argument('--model_type', type=str, choices=['glm-4', 'glm-3.5-turbo', 'chatglm3-6b'],
                              help='model type of zhipu, refer to: https://open.bigmodel.cn/dev/api')
    zhipu_parser.add_argument('--key', type=str, help='api key of zhipu', default="")
    zhipu_parser.add_argument('--address', type=str, help='base url of zhipu', default="127.0.0.1:8989")

    tongyi_parser = subparsers.add_parser('tongyi', help='using alibaba tongyi qwen')
    tongyi_parser.add_argument('--model_type', type=str, choices=['qwen-max', 'qwen-max-1201', 'qwen-max-longcontext',
                                                                  'qwen-turbo', 'qwen-plus'])
    tongyi_parser.add_argument('--key', type=str, help='api key of tongyi qwen')

    openai_local_parser = subparsers.add_parser('openai_local', help='using model deployed by framework support openai API')
    openai_local_parser.add_argument('--address', help='server ip:port, default to 127.0.0.1:8080',
                             default='127.0.0.1:8080')
    openai_local_parser.add_argument('--model_type', choices=supported_model_list,
                             help='specify model name used.')
    openai_local_parser.add_argument("--server_type", help="deployment framework, "
            "due to swift's model name is different, we need a map", default="other", choices=["other", "swift"])
    openai_local_parser.add_argument('--max_tokens', type=int, default=0)
    openai_local_parser.add_argument("--add_llama3_stop", action="store_true", default=False,
                        help="llama3 has some special stop token. Some server(sglang, swift) did not follow."
                             "So if you use this framework to deploy. You may need to use this argument."
                             "Or llama3 will continously generate new token until reach max_output_num.")

def build_arg_parser():
    parser = argparse.ArgumentParser(description="Command-line tool to analyze projects.")
    parser.add_argument("--root_path", type=str, required=True, help="root path of all benchmarks.")
    parser.add_argument("--llm_strategy", type=str, choices=['none', 'single', 'sea'],
                        default='none')
    parser.add_argument("--base_analyzer", type=str, choices=['flta', 'mlta', 'kelp'], default='flta')
    parser.add_argument("--ablation_type", type=int, default=0, choices=list(range(8)),
                        help="ablation type: 0 -> no ablation, "
                          "1 -> w/o caller local, 2 -> w/o caller global, "
                          "3 -> w/o callee local, 4 -> w/o callee global, "
                          "5 -> w/o local, 6 -> w/o global,"
                          "7 -> w/o all")
    parser.add_argument("--analyze_all", action="store_true", default=False,
                        help="Analyze all dumped icall in benchmark. Without evaluation")

    parser.add_argument("--debug", action="store_true", default=False,
                        help="If true, set to debug mode")
    parser.add_argument("--log_llm_output", action="store_true", default=False,
                        help="If true, log llm output to log file")
    parser.add_argument("--log_total_info", action="store_true", default=False,
                        help="log total distribution of flta, mlta, kelp cases if set to true")
    parser.add_argument("--log_flta_case_info", action="store_true", default=False)

    # 添加--project参数，并设置nargs='+'，以接受一个或多个值
    parser.add_argument("--projects", type=str, help="One or more projects to analyze")
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

    # prompt时添加注释信息
    parser.add_argument("--add_comment", action="store_true", default=False)
    parser.add_argument("--no_cot", action="store_true", default=False)

    # double_prompt表示是否采用二段式prompt策略
    parser.add_argument("--double_prompt", action="store_true", default=False)
    parser.add_argument("--only_count_scope", action="store_true", default=False, help="only count ground_truth in scope")

    parser.add_argument("--enable_analysis_for_macro", action="store_true", default=False,
                        help="enable analysis for macro callsite")
    parser.add_argument("--disable_analysis_for_normal", action="store_true", default=False,
                        help="disable analysis for normal callsite")

    parser.add_argument("--enable_semantic_for_mlta", action="store_true", default=False)
    parser.add_argument("--disable_llm_for_uncertain", action="store_true", default=False)
    parser.add_argument("--evaluate_uncertain", action="store_true", default=False,
                        help="enable cast between void* or char* with other pointer type")

    parser.add_argument("--log_res_to_file", action="store_true", default=False,
                        help="If true, will log analysis result to file.")
    parser.add_argument("--disable_system_prompt", action="store_true", default=False)

    # 投票次数
    parser.add_argument("--vote_time", type=int, default=5, help="Vote time for llm.")
    # 评估GPT在传统类型分析无法确定的部分的分析效果
    parser.add_argument("--evaluate_soly_for_llm", action="store_true", default=False,
                        help="If true, the tool will analyze How gpt perform when type analysis cannot determine.")
    add_subparser(parser)
    return parser

def main():
    parser = build_arg_parser()
    args = parser.parse_args()
    root_path: str = args.root_path
    # 检查是否提供了项目参数
    if not args.projects:
        parser.error("You must specify one or more project to analyze")
    projects: List[str] = args.projects.split(',')

    logging.basicConfig()
    logger = logging.getLogger("CodeAnalyzer")
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)  # 设置handler的级别，可以与logger级别一致或更具体
    # 创建一个Formatter来格式化输出的日志信息
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    # 将创建的handler添加到logger中
    logger.addHandler(handler)
    if args.debug:
        logger.setLevel(level=logging.DEBUG)
    else:
        logger.setLevel(level=logging.INFO)

    if args.llm in {"openai_local", "gpt", "google", "zhipu", "tongyi"}:
        model_name = args.model_type
    else:
        model_name = ""

    semantic_res_prec: List[float] = []
    semantic_res_recall: List[float] = []
    semantic_res_f1: List[float] = []

    flta_res_prec: List[float] = []
    flta_res_recall: List[float] = []
    flta_res_f1: List[float] = []

    failed_type_cases: List[str] = []
    success_type_cases: List[str] = []
    label_nums: List[int] = []
    flta_nums: List[int] = []
    seman_nums: List[int] = []
    macro_cases: List[str] = []

    local_failed_cases: List[str] = []
    global_failed_cases: List[str] = []
    analyzed_cases: Set[str] = set()

    precisions: List[float] = []
    recalls: List[float] = []
    f1s: List[float] = []

    mlta_successful_cases: List[str] = list()
    mlta_nums: List[int] = list()
    mlta_seman_nums: List[int] = list()
    mlta_label_nums: List[int] = list()
    mlta_res_prec: List[float] = list()
    mlta_res_recall: List[float] = list()
    mlta_res_f1: List[float] = list()
    mlta_seman_res_prec: List[float] = list()
    mlta_seman_res_recall: List[float] = list()
    mlta_seman_res_f1: List[float] = list()
    kelp_cases: List[str] = list()

    # 打印项目参数的值
    for project in projects:
        logging.getLogger("CodeAnalyzer").info(f"analyzing project: {project}")
        project_included_func_file = os.path.join(root_path, "infos", "funcs", f"{project}.txt")
        target_info_dir = "static_icall_infos" if args.analyze_all else "icall_infos"
        icall_infos_file = os.path.join(root_path, "infos", target_info_dir, f"{project}.txt")
        project_root = os.path.join(root_path, "projects", project)
        project_analyzer = ProjectAnalyzer(project_included_func_file, icall_infos_file, project_root, args,
                                           project, model_name)
        items, results = project_analyzer.evaluate()

        precisions.append(results[0])
        recalls.append(results[1])
        f1s.append(results[2])

        semantic_res_prec.extend(items[0])
        semantic_res_recall.extend(items[1])
        semantic_res_f1.extend(items[2])
        flta_res_prec.extend(items[3])
        flta_res_recall.extend(items[4])
        flta_res_f1.extend(items[5])
        failed_type_cases.extend(items[6])
        success_type_cases.extend(items[7])
        macro_cases.extend(items[8])
        label_nums.extend(items[9])
        flta_nums.extend(items[10])
        seman_nums.extend(items[11])
        local_failed_cases.extend(items[12])
        analyzed_cases.update(items[13])
        for case in items[14]:
            if case not in macro_cases:
                global_failed_cases.append(case)

        mlta_successful_cases.extend(items[15])
        mlta_nums.extend(items[16])
        mlta_seman_nums.extend(items[17])
        mlta_label_nums.extend(items[18])
        mlta_res_prec.extend(items[19])
        mlta_res_recall.extend(items[20])
        mlta_res_f1.extend(items[21])
        mlta_seman_res_prec.extend(items[22])
        mlta_seman_res_recall.extend(items[23])
        mlta_seman_res_f1.extend(items[24])

        kelp_cases.extend(items[25])


    mean = lambda res: sum(res) * 100 / len(res)
    print("total mean result: {:.1f} | {:.1f} | {:.1f} |".format(mean(precisions),
                                                                 mean(recalls), mean(f1s)))
    if len(semantic_res_prec) != 0:
        print("successfully analyze {} icalls with flta".format(len(semantic_res_prec)))
        print("{} icalls fail to be analyzed by flta, among them {} are macro callsites".
              format(len(failed_type_cases), len(macro_cases)))
        print("{} icalls are local failed cases, {} are global failed cases.".format(len(local_failed_cases), len(global_failed_cases)))

        print("semantic res | {:.1f} | {:.1f} | {:.1f} |".format(mean(semantic_res_prec),
                                                                        mean(semantic_res_recall),
                                                                        mean(semantic_res_f1)))
        print("flta res | {:.1f} | {:.1f} | {:.1f} |".format(mean(flta_res_prec),
                                                                        mean(flta_res_recall),
                                                                        mean(flta_res_f1)))

        if args.log_flta_case_info:
            lines = ["callsite_key,label_num,flta_num,seman_num,seman_prec,seman_recall,seman_f1,flta_prec,flta_recall,flta_f1"]
            assert all(len(lst) == len(success_type_cases) for lst in [semantic_res_prec,
                semantic_res_recall, semantic_res_f1, flta_res_prec, flta_res_recall, flta_res_f1,
                flta_nums, label_nums])

            for callsite_key, label_num, flta_num, seman_num, semantic_prec, semantic_recall, semantic_f1,\
                    flta_prec, flta_recall, flta_f1 in \
                    zip(success_type_cases, label_nums, flta_nums, seman_nums, semantic_res_prec,
                            semantic_res_recall, semantic_res_f1, flta_res_prec, flta_res_recall, flta_res_f1):
                lines.append("{},{},{},{},{:.1f},{:.1f},{:.1f},{:.1f},{:.1f},{:.1f}".format(callsite_key, label_num, flta_num, seman_num,
                                   semantic_prec * 100, semantic_recall * 100, semantic_f1 * 100,
                                   flta_prec * 100, flta_recall * 100, flta_f1 * 100))
                suffix_ = suffix[args.ablation_type] + "wc_" if args.add_comment else suffix[args.ablation_type]
                log_dir = "experimental_logs/{}_{}analysis/{}/{}-{}".format(mapping[args.llm_strategy], suffix_, args.running_epoch,
                                                                          model_name, args.temperature)
                open("{}/flta_case_info.csv".format(log_dir), 'w', encoding='utf-8').write("\n".join(lines))

    print("successfully analyze {} icalls with kelp".format(len(kelp_cases)))

    if len(mlta_successful_cases) > 0:
        print("successfully analyze {} icalls with mlta".format(len(mlta_successful_cases)))
        print("mlta semantic res | {:.1f} | {:.1f} | {:.1f} |".format(mean(mlta_seman_res_prec),
                                                                 mean(mlta_seman_res_recall),
                                                                 mean(mlta_seman_res_f1)))
        print("mlta res | {:.1f} | {:.1f} | {:.1f} |".format(mean(mlta_res_prec),
                                                             mean(mlta_res_recall),
                                                             mean(mlta_res_f1)))

        if args.log_flta_case_info:
            lines = ["callsite_key,label_num,mlta_num,seman_num,seman_prec,seman_recall,seman_f1,mlta_prec,mlta_recall,mlta_f1"]
            assert all(len(lst) == len(mlta_successful_cases) for lst in [mlta_seman_res_prec,
                mlta_seman_res_recall, mlta_seman_res_f1, mlta_res_prec, mlta_res_recall, mlta_res_f1,
                mlta_nums, mlta_label_nums])

            for callsite_key, label_num, mlta_num, seman_num, semantic_prec, semantic_recall, semantic_f1,\
                    mlta_prec, mlta_recall, mlta_f1 in \
                    zip(mlta_successful_cases, mlta_label_nums, mlta_nums, mlta_seman_nums, mlta_seman_res_prec,
                            mlta_seman_res_recall, mlta_seman_res_f1, mlta_res_prec, mlta_res_recall, mlta_res_f1):
                lines.append("{},{},{},{},{:.1f},{:.1f},{:.1f},{:.1f},{:.1f},{:.1f}".format(callsite_key, label_num, mlta_num, seman_num,
                                   semantic_prec * 100, semantic_recall * 100, semantic_f1 * 100,
                                   mlta_prec * 100, mlta_recall * 100, mlta_f1 * 100))
                log_dir = "experimental_logs/{}_{}analysis/{}/{}-{}".format(mapping[args.llm_strategy], suffix[args.ablation_type], args.running_epoch,
                                                                          model_name, args.temperature)
                open("{}/mlta_case_info.csv".format(log_dir), 'w', encoding='utf-8').write("\n".join(lines))

if __name__ == '__main__':
    main()