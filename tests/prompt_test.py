from llm_analyzer.llm_prompts.gpt_prompt import SystemPrompt1, UserPrompt1, \
    UserPrompt2, SystemPrompt1_, UserPrompt1_
import openai
import sys
from typing import List

icall_context: List[str] = [
    "ngx_log_t *log",
    "u_char      *p, *last, *msg;",
    "p = log->handler(log, p, last - p);"
]

func_declarator = """char *  
ngx_conf_set_sec_slot(ngx_conf_t *cf, ngx_command_t *cmd, void *conf)"""

if __name__ == '__main__':
    api_key = sys.argv[1]
    openai.api_key = api_key

    dialog1 = [{"role": "system", "content": SystemPrompt1},
               {"role": "user",
                "content": UserPrompt1.format(icall_context[-1], "\n".join(icall_context)
                                               , "\n\n".join(func_declarator))}]
    print(UserPrompt1.format(icall_context[-1], "\n".join(icall_context)
                                               , func_declarator))
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=dialog1
    )
    content1 = response.choices[0]["message"]["content"]
    print(content1)

    dialog2 = [{"role": "user",
                "content": UserPrompt2.format(content1)}]
    response2 = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=dialog2
    )
    content2 = response2.choices[0]["message"]["content"]
    print(content2)