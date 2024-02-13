import sys
from zhipuai import ZhipuAI
from zhipuai.api_resource.chat.completions import Completion

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

def test_icall_decl(client: ZhipuAI, model_type: str):
    response: Completion = client.chat.completions.create(
        model=model_type,  # 填写需要调用的模型名称
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    print(response.choices[0].message.content)
    print(type(response.choices[0].message))
    print("=================")
    print("input token: {}".format(response.usage.prompt_tokens))
    print("output token: {}".format(response.usage.completion_tokens))
    print("total token: {}".format(response.usage.total_tokens))


def main():
    api_key = sys.argv[1]
    model_type = sys.argv[2]
    if not api_key.startswith("http://"):
        client = ZhipuAI(api_key=api_key)
    else:
        client = ZhipuAI(api_key="EMP.TY", base_url=api_key)
    test_icall_decl(client, model_type)

if __name__ == '__main__':
    main()