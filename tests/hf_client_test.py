import requests
import json

def test_icall_decl(address: str, double: bool=False):
    from test_data import context, summ
    if not double:
        context = context + "\n" + summ

    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "inputs": context,
        "parameters": {"max_new_tokens": 1024,
                       "temperature": 0.5}
    }
    print("query is:")
    print(context)
    print("===========================")
    server_url = "http://" + address + "/generate"  # 替换为实际的服务器地址和端口
    # 发送POST请求，将JSON数据发送到server
    response = requests.post(server_url, headers=headers, data=json.dumps(data))

    # 检查服务器的响应状态码
    if response.status_code == 200 and not response.text.startswith("Invalid:"):
        # 解析服务器的字符串响应
        response_data_json: dict = json.loads(response.text)
        print("Response from server:\n", response_data_json['generated_text'])
    else:
        print("Error: Server returned a non-200 status code or encounter invalid result")

import sys

if __name__ == '__main__':
    address = sys.argv[1]
    flag = bool(sys.argv[2])
    test_icall_decl(address, flag)