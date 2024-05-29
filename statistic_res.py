import argparse
import os

suffix = ["", "wo_caller_local_", "wo_caller_global_", "wo_callee_local_", "wo_callee_global_",
          "wo_local_", "wo_global_"]

def build_parser():
    parser = argparse.ArgumentParser(description="Command-line tool to count result.")
    parser.add_argument("--analysis_type", type=str, choices=['single_step_{}analysis',
                                                              'addr_site_v2_{}analysis'])
    parser.add_argument("--ablation_type", type=int, default=0, choices=list(range(7)),
                        help="ablation type: 0 -> no ablation, "
                             "1 -> w/o caller local, 2 -> w/o caller global, "
                             "3 -> w/o callee local, 4 -> w/o callee global")
    parser.add_argument("--base_analyzer", type=str, choices=['flta', 'mlta', 'kelp', 'none'])
    parser.add_argument("--enable_semantic_for_mlta", action="store_true", default=False)
    parser.add_argument("--res_type", type=str, default='normal', choices=['normal', 'binary', 'token'])
    parser.add_argument("--running_epoch", type=int, default=1, help="Epoch num for current running")
    parser.add_argument("--model_type", type=str, choices=['qwen', 'chatglm',
                                                           'text-bison-001',
                                                           'chat-bison-001',
                                                           'gemini-pro',
                                                           'qwen-max',
                                                           'Qwen1.5-14B-Chat',
                                                           'Qwen1.5-32B-Chat',
                                                           'Qwen1.5-72B-Chat',
                                                           'llama-3-70b-instruct',
                                                           'Phi-3-mini-128k-instruct',
                                                           'codegemma-1.1-7b-it',
                                                           'Yi-1.5-34B-Chat'])
    parser.add_argument("--temperature", type=float, default=0,
                        help="temperature for llm")
    parser.add_argument("--projects", type=lambda s: s.split(','), help="One or more projects to analyze")

    return parser


def analyze(base_analyzer, enable_semantic_for_mlta, running_epoch, analysis_type, model_type, temperature, project):
    filename = "evaluation_result.txt"
    if base_analyzer != "none":
        info = base_analyzer
        if enable_semantic_for_mlta:
            info += "_seman"
        filename = f"evaluation_result_{info}.txt"
    file_path = f'experimental_logs/{analysis_type}/{running_epoch}/' \
                f'{model_type}-{temperature}/{project}/{filename}'
    # assert os.path.exists(file_path)
    if not os.path.exists(file_path):
        print("missing project: {}".format(project))
        return 0, 0, 0
    lines = open(file_path).readlines()
    line = lines[0].strip()
    prec_str, recall_str, f1_str = line.split(',')
    prec = float(prec_str) / 100
    recall = float(recall_str) / 100
    f1 = float(f1_str) / 100
    return prec, recall, f1

def analyze_token(base_analyzer, enable_semantic_for_mlta, running_epoch, analysis_type, model_type, temperature, project):
    filename = "evaluation_result.txt"
    if base_analyzer != "none":
        info = base_analyzer
        if enable_semantic_for_mlta:
            info += "_seman"
        filename = f"evaluation_result_{info}.txt"
    file_path = f'experimental_logs/{analysis_type}/{running_epoch}/' \
                f'{model_type}-{temperature}/{project}/{filename}'
    if not os.path.exists(file_path):
        print("missing project: {}".format(project))
        return 0, 0, 0
    lines = open(file_path).readlines()
    line = lines[2].strip()
    input_token_num_str, output_token_num_str = line.split(',')[:2]
    return float(input_token_num_str), float(output_token_num_str)


def analyze_binary(base_analyzer, enable_semantic_for_mlta, running_epoch, analysis_type, model_type, temperature, project):
    filename = "evaluation_result.txt"
    if base_analyzer != "none":
        info = base_analyzer
        if enable_semantic_for_mlta:
            info += "_seman"
        filename = f"evaluation_result_{info}.txt"
    file_path = f'experimental_logs/{analysis_type}/{running_epoch}/' \
                f'{model_type}-{temperature}/{project}/{filename}'

    if not os.path.exists(file_path):
        print("missing project: {}".format(project))
        return 0, 0, 0, 0, 0, 0
    lines = open(file_path).readlines()
    line = lines[1].strip()
    acc_str, prec_str, recall_str, f1_str, fpr_str, fnr_str = line.split(',')

    acc = float(acc_str) / 100
    prec = float(prec_str) / 100
    recall = float(recall_str) / 100
    f1 = float(f1_str) / 100
    fpr = float(fpr_str) / 100
    fnr = float(fnr_str) / 100

    return acc, prec, recall, f1, fpr, fnr


def analyze_all_project_binary(base_analyzer, enable_semantic_for_mlta, running_epoch, analysis_type, model_type, temperature, projects):
    acc_list = []
    prec_list = []
    recall_list = []
    f1_list = []
    fpr_list = []
    fnr_list = []

    for project in projects:
        acc, prec, recall, f1, fpr, fnr = \
            analyze_binary(base_analyzer, enable_semantic_for_mlta, running_epoch, analysis_type, model_type, temperature, project)
        acc_list.append(acc)
        prec_list.append(prec)
        recall_list.append(recall)
        f1_list.append(f1)
        fpr_list.append(fpr)
        fnr_list.append(fnr)
        print(f"| {project}-{model_type}-{temperature} "
              f"| {(acc * 100):.1f} | {(prec * 100):.1f} | {(recall * 100):.1f} | "
              f"{(f1 * 100):.1f} | {(fpr * 100):.1f} | {(fnr * 100):.1f} |")

    avg_acc = sum(acc_list) / len(acc_list)
    avg_prec = sum(prec_list) / len(prec_list)
    avg_recall = sum(recall_list) / len(recall_list)
    avg_f1 = sum(f1_list) / len(f1_list)
    avg_fpr = sum(fpr_list) / len(fpr_list)
    avg_fnr = sum(fnr_list) / len(fnr_list)
    print(f"| avg-{model_type}-{temperature} "
          f"| {(avg_acc * 100):.1f} | {(avg_prec * 100):.1f} | {(avg_recall * 100):.1f} | "
          f"{(avg_f1 * 100):.1f} | {(avg_fpr * 100):.1f} | {(avg_fnr * 100):.1f} |")
    return avg_prec, avg_recall, avg_f1


def analyze_all_project(base_analyzer, enable_semantic_for_mlta, running_epoch, analysis_type, model_type, temperature, projects):
    prec_list = []
    recall_list = []
    f1_list = []
    for project in projects:
        prec, recall, f1 = analyze(base_analyzer, enable_semantic_for_mlta, running_epoch, analysis_type, model_type, temperature, project)
        prec_list.append(prec)
        recall_list.append(recall)
        f1_list.append(f1)
        print(f"| {project}-{model_type}-{temperature} "
                     f"| {(prec * 100):.1f} | {(recall * 100):.1f} | {(f1 * 100):.1f} |")

    avg_prec = sum(prec_list) / len(prec_list)
    avg_recall = sum(recall_list) / len(recall_list)
    avg_f1 = sum(f1_list) / len(f1_list)
    print(f"| avg-{model_type}-{temperature} "
                 f"| {(avg_prec * 100):.1f} | {(avg_recall * 100):.1f} | {(avg_f1 * 100):.1f} |")
    return avg_prec, avg_recall, avg_f1


def analyze_all_project_token(base_analyzer, enable_semantic_for_mlta, running_epoch, analysis_type, model_type, temperature, projects):
    input_token_total_num = 0
    output_token_total_num = 0
    for project in projects:
        input_token_num, output_token_num = analyze_token(base_analyzer, enable_semantic_for_mlta, running_epoch, analysis_type,
                                                              model_type, temperature, project)
        input_token_total_num += input_token_num
        output_token_total_num += output_token_num

        print(f"| {project}-{model_type}-{temperature} "
              f"| {input_token_num} | {output_token_num} |")

    print(f"| total-{model_type}-{temperature} "
          f"| {input_token_total_num} | {output_token_total_num} |")


def main():
    parser = build_parser()
    args = parser.parse_args()
    running_epoch = args.running_epoch
    analysis_type = args.analysis_type.format(suffix[args.ablation_type])
    model_type = args.model_type
    temperature = args.temperature
    projects = args.projects
    base_analyzer = args.base_analyzer
    enable_semantic_for_mlta = args.enable_semantic_for_mlta

    if args.res_type == 'binary':
        analyze_all_project_binary(base_analyzer, enable_semantic_for_mlta, running_epoch, analysis_type, model_type, temperature, projects)
    elif args.res_type == 'normal':
        analyze_all_project(base_analyzer, enable_semantic_for_mlta, running_epoch, analysis_type, model_type, temperature, projects)
    elif args.res_type == 'token':
        analyze_all_project_token(base_analyzer, enable_semantic_for_mlta, running_epoch, analysis_type, model_type, temperature, projects)



if __name__ == '__main__':
    main()