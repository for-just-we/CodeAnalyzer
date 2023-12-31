import sys
from huggingface_hub import InferenceClient

def test_icall_decl(client: InferenceClient, double: bool=False):
    from test_data import context, summ
    if not double:
        context = context + "\n" + summ
    print("query is:")
    print(context)
    print("===========================")
    response: str = client.text_generation(context)
    print("response is:")
    print(response)

if __name__ == '__main__':
    address = sys.argv[1]
    flag = bool(sys.argv[2])
    client = InferenceClient(address)
    test_icall_decl(client)