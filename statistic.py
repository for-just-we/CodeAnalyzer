import csv
import sys

def calculate_average_diff(file_name):
    # 读取CSV文件
    with open(file_name, 'r') as file:
        reader = csv.reader(file)
        data = list(reader)

    # 初始化变量用于计算差值和总和
    total_prec_diff = 0
    total_recall_diff = 0
    total_f1_diff = 0
    num_rows = len(data)

    prec_raw = 0
    recall_raw = 0
    f1_raw = 0

    prec_llm = 0
    recall_llm = 0
    f1_llm = 0

    # 计算每两行之间的差值并累加总和
    for i in range(1, num_rows, 2):
        prec_diff = float(data[i][1]) - float(data[i-1][1])
        recall_diff = float(data[i][2]) - float(data[i-1][2])
        f1_diff = float(data[i][3]) - float(data[i-1][3])

        prec_raw += float(data[i-1][1])
        recall_raw += float(data[i-1][2])
        f1_raw += float(data[i-1][3])

        prec_llm += float(data[i][1])
        recall_llm += float(data[i][2])
        f1_llm += float(data[i][3])

        total_prec_diff += prec_diff
        total_recall_diff += recall_diff
        total_f1_diff += f1_diff

    # 计算平均值
    avg_prec_diff = total_prec_diff / num_rows * 2
    avg_recall_diff = total_recall_diff / num_rows * 2
    avg_f1_diff = total_f1_diff / num_rows * 2

    avg_prec_raw = prec_raw / num_rows * 2
    avg_recall_raw = recall_raw / num_rows * 2
    avg_f1_raw = f1_raw / num_rows * 2

    avg_prec_llm = prec_llm / num_rows * 2
    avg_recall_llm = recall_llm / num_rows * 2
    avg_f1_llm = f1_llm / num_rows * 2

    # 打印结果
    print(f'平均prec差值: {avg_prec_diff}')
    print(f'平均recall差值: {avg_recall_diff}')
    print(f'平均f1差值: {avg_f1_diff}')

    print(f'平均prec raw: {avg_prec_raw}')
    print(f'平均recall raw: {avg_recall_raw}')
    print(f'平均f1 raw: {avg_f1_raw}')

    print(f'平均prec llm: {avg_prec_llm}')
    print(f'平均recall llm: {avg_recall_llm}')
    print(f'平均f1 llm: {avg_f1_llm}')


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("请提供正确的文件名作为命令行参数")
    else:
        file_name = sys.argv[1]
        calculate_average_diff(file_name)
