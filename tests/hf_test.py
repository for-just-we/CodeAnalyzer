import sys
from huggingface_hub import InferenceClient

def test_icall_decl(client: InferenceClient, double: bool=False):
    from test_data import context, summ
    input = context
    if not double:
        input = input + "\n" + summ
    print("query is:")
    print(input)
    print("===========================")
    response: str = client.text_generation(input, max_new_tokens=1024)
    print("response is:")
    print(response)

if __name__ == '__main__':
    address = sys.argv[1]
    flag = sys.argv[2] == "True"
    client = InferenceClient(model="http://" + address)
    test_icall_decl(client, flag)