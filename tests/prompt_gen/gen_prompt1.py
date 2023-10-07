from llm_analyzer.llm_prompts import PREFIX, FORMAT_INSTRUCTIONS, QUESTION_PROMPT

if __name__ == '__main__':
    callsite = "p = log->handler(log, p, last - p);"
    callees: str = "ngx_conf_set_sec_slot,ngx_stream_ssl_preread_merge_srv_conf," \
                   "ngx_conf_set_str_slot,ngx_str_rbtree_insert_value,ngx_stream_ssl_static_variable," \
                   "ngx_http_proxy_internal_body_length_variable," \
                   "ngx_http_proxy_cookie_domain,ngx_load_module," \
                   "ngx_thread_pool"

    final_prompt = PREFIX + "\n" + FORMAT_INSTRUCTIONS + "\n"\
                   + QUESTION_PROMPT.format(callsite, callees)
    print(final_prompt)