from varclr.encoders import BERT_Encoder

if __name__ == '__main__':
    model_path = "../../models/varclr_bert"
    encoder = BERT_Encoder.load(model_path)

    arg_name: str = "writer"
    param_names: set[str] = {"ngx_log_error","ngx_ssl_get_cached_session",
                             "ngx_http_ssl_npn_advertised","ngx_http_v2_filter_get_shadow",
                             "ngx_http_xslt_sax_external_subset","ngx_http_xslt_sax_error",
                             "ngx_log_memory_writer","ngx_http_log_error_handler","ngx_syslog_writer",
                             "ngx_ssl_password_callback"}
    for param_name in param_names:
        print(f"{encoder.score(arg_name, param_name):.2f}", end=", ")
    print()