import requests
import json
from llm_utils.preprocess_prompt import preprocess_prompt

def query(address: str, prompt: str):
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 1024,
                       "temperature": 0.5}
    }
    print("query is:")
    print(input)
    print("===========================")
    server_url = "http://" + address + "/generate"  # 替换为实际的服务器地址和端口
    # 发送POST请求，将JSON数据发送到server
    response = requests.post(server_url, headers=headers, data=json.dumps(data))

    # 检查服务器的响应状态码
    if response.status_code == 200 and not response.text.startswith("Invalid:"):
        # 解析服务器的字符串响应
        response_data_json: dict = json.loads(response.text)
        print("Response from server:\n", response_data_json['generated_text'])
        resp = response_data_json['generated_text']
    else:
        print("Error: Server returned a non-200 status code or encounter invalid result")
        resp = "ERROR"

    return resp


def test_icall_decl(model_type: str, address: str):
    from ..test_data1 import system_prompt, user_prompt
    from llm_utils.common_prompt import summarizing_prompt

    prompt = preprocess_prompt(model_type, [system_prompt, user_prompt])
    resp = query(address, prompt)

    tokens = resp.split(" ")
    if len(tokens) >= 8:
        input_prompt = summarizing_prompt.format(resp)
        prompt = preprocess_prompt(model_type, [input_prompt])
        resp = query(address, prompt)