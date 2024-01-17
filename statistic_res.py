import argparse
import os
import logging

def build_parser():
    parser = argparse.ArgumentParser(description="Command-line tool to count result.")
    parser.add_argument("--analysis_type", type=str, choices=['single_step_analysis',
                                                              'single_step_complex_analysis',
                                                              'semantic_analysis'])
    parser.add_argument("--running_epoch", type=int, default=1, help="Epoch num for current running")
    parser.add_argument("--model_type", type=str, choices=['codellama', 'wizardcoder',
                                                           'text-bison-001',
                                                           'chat-bison-001',
                                                           'gemini-pro'])
    parser.add_argument("--temperature", type=float, default=0,
                        help="temperature for llm")
    parser.add_argument("--projects", nargs='+', help="One or more projects to analyze")

    return parser


def analyze(running_epoch, analysis_type, model_type, temperature, project):
    file_path = f'experimental_logs/{analysis_type}/{running_epoch}/' \
                f'{model_type}-{temperature}/{project}/evaluation_result.txt'
    assert os.path.exists(file_path)
    lines = open(file_path).readlines()
    line = lines[0].strip()
    prec_str, recall_str, f1_str = line.split(',')
    prec = float(prec_str)
    recall = float(recall_str)
    f1 = 2 * prec * recall / (prec + recall)
    return prec, recall, f1


def analyze_all_project(running_epoch, analysis_type, model_type, temperature, projects):
    prec_list = []
    recall_list = []
    f1_list = []
    for project in projects:
        prec, recall, f1 = analyze(running_epoch, analysis_type, model_type, temperature, project)
        prec_list.append(prec)
        recall_list.append(recall)
        f1_list.append(f1)
        logging.info(f"| {project}-{model_type}-{temperature} "
                     f"| {(prec * 100):.1f} | {(recall * 100):.1f} | {(f1 * 100):.1f} |")

    avg_prec = sum(prec_list) / len(prec_list)
    avg_recall = sum(recall_list) / len(recall_list)
    avg_f1 = sum(f1_list) / len(f1_list)
    logging.info(f"| avg-{model_type}-{temperature} "
                 f"| {(avg_prec * 100):.1f} | {(avg_recall * 100):.1f} | {(avg_f1 * 100):.1f} |")
    return avg_prec, avg_recall, avg_f1



def main():
    parser = build_parser()
    args = parser.parse_args()
    running_epoch = args.running_epoch
    analysis_type = args.analysis_type
    model_type = args.model_type
    temperature = args.temperature
    projects = args.projects

    analyze_all_project(running_epoch, analysis_type, model_type, temperature, projects)