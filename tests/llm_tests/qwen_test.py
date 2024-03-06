import sys
from http import HTTPStatus
import dashscope

system_prompt = """You are a text analyzer tasked with analyzing the similarity between two declarators."""

user_prompt = """Given a function pointer declarator and a function declarator, your task is to evaluate whether the parameter types of function pointer can match that of the function in following steps:

- 1.Extract the parameter list separately from both the function pointer declarator and the function declarator.

- 2.Compare each parameter's type individually for a match, ensuring identical names and pointer hierarchies for types to match.

Note that:

- 1.Certain parameter declarations may be wrapped or followed by macros like UNUSED_PARAM or unused, which do not impact the parameter type. For example, UNUSED_PARAM(int var) matches the type of int var.

- 2.Types like int, long, size_t could be considered as compatible due to implicit cast.

The function pointer declarator is 

typedef int (*ssh_packet_callback) (ssh_session session, uint8_t type, ssh_buffer packet, void *user);

The function declarator is

int
sftp_channel_default_subsystem_request(UNUSED_PARAM(ssh_session session),
                                       UNUSED_PARAM(ssh_channel channel),
                                       UNUSED_PARAM(const char *subsystem),
                                       UNUSED_PARAM(void *userdata))
"""

from dashscope.common.error import RequestFailure

def call_with_messages(api_key):
    messages = [{'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}]
    try:
        response = dashscope.Generation.call(
            dashscope.Generation.Models.qwen_max,
            messages=messages,
            api_key = api_key,
            result_format='message',  # set the result to be "message" format.
            temperature=0.5
        )
    except RequestFailure as e:
        if int(e.http_code) == 429:
            print("catch rate limit")
        else:
            print("catch other error")
    except Exception as e:
        print("catch error")

    if response.status_code == HTTPStatus.OK:
        print(response)
        resp: str = response["output"]["choices"][0]["message"]["content"]
        input_token_num: int = response["usage"]["input_tokens"]
        output_token_num: int = response["usage"]["output_tokens"]

        print("response is: {}".format(resp))
        print("input token num: {} , output token num: {}".format(input_token_num, output_token_num))
    elif response.status_code == 429:
        print("rate limit")
    else:
        print('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
            response.request_id, response.status_code,
            response.code, response.message
        ))


def multi_thread_test(api_key):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from tqdm import tqdm

    pbar = tqdm(total=120, desc="test")

    def update_progress(future):
        pbar.update(1)

    def worker():
        call_with_messages(api_key)

    executor = ThreadPoolExecutor(max_workers=120)
    futures = []
    for i in range(120):
        future = executor.submit(worker)
        future.add_done_callback(update_progress)
        futures.append(future)

if __name__ == '__main__':
    multi_thread_test(sys.argv[1])
