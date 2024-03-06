import sys
import google.generativeai as genai
from google.generativeai import GenerativeModel
from google.generativeai.types.generation_types import GenerateContentResponse, GenerationConfig
from google.api_core.exceptions import ResourceExhausted
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# currently the default temperature of gemini is 0.4
def list_models():
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m)
            print(m.name)

def simple_multi_thread_test(model: GenerativeModel):
    # response是一个genai.types.generation_types.GenerateContentResponse对象
    executor = ThreadPoolExecutor(max_workers=60)

    def worker(id: int):
        while True:
            try:
                response: GenerateContentResponse = model.generate_content(
                    "What is the meaning of life?")
                print("The text response of {}-th request is:\n\n"
                      "{}\n================================\n\n".format(id + 1, response.text))
                break
            except ResourceExhausted as e:
                print("ResourceExhausted in {}-th request".format(id + 1))
                time.sleep(60)
                continue

    futures = []
    for i in range(60):
        future = executor.submit(worker, i)
        futures.append(future)

    for future in as_completed(futures):
        future.result()

def test_icall_decl(model: GenerativeModel):
    from ..test_data import context
    response: GenerateContentResponse = model.generate_content(
        context)
    print(response.text)

#     summarizing = """If the following text provides a positive response, answer with only 'yes'; else if it provides a negative response, answer with only 'no'.
#
# {}
#     """
#     summary_resp: GenerateContentResponse = model.generate_content(summarizing.format(response.text))
#     print("==================")
#     print(summary_resp.text)

def main():
    api_key = sys.argv[1]
    genai.configure(api_key=api_key)

    list_models()

    config = GenerationConfig(temperature=0.8)
    model: GenerativeModel = GenerativeModel('gemini-pro', generation_config=config)
    print("==================")
    print(model)
    test_icall_decl(model)


if __name__ == '__main__':
    main()