from typing import Set, List

import torch
import torch.nn.functional as F
from transformers import RobertaTokenizer, RobertaModel

from varclr.config import codebert_model_path

class TestSim:
    def __init__(self, model_path: str):
        self.tokenizer = RobertaTokenizer.from_pretrained(model_path)
        self.model = RobertaModel.from_pretrained(model_path)
        self.model = self.model.eval()

    def vectorize(self, code_text: str):
        code_tokens: List[str] = [self.tokenizer.cls_token] + \
                                 self.tokenizer.tokenize(code_text) + [self.tokenizer.eos_token]
        token_ids: List[int] = self.tokenizer.convert_tokens_to_ids(code_tokens)
        vectorized_ids: torch.Tensor = torch.tensor(token_ids).unsqueeze(0)
        output = self.model(vectorized_ids)
        last_embedding = output.pooler_output  # shape = [1, 768]

        return last_embedding[0]


def test_callsite_sim(icallsite: str, func_names: Set[str], test_sim: TestSim):
    callsite_embedding = test_sim.vectorize(icallsite)
    func_embeddings = [test_sim.vectorize(func_name) for func_name in func_names]
    sims = [F.cosine_similarity(callsite_embedding, func_embedding, dim=0).item()
            for func_embedding in func_embeddings]

    for sim in sims:
        print(f"{sim:.2f}", end=", ")
    print()

if __name__ == '__main__':
    test_sim = TestSim(codebert_model_path)
    icallsite = "ngx_log_t *log\n  u_char      *p, *last, *msg;\n  log->handler(log, p, last - p)"
    from tests.filter_test.testcase1 import *
    func_names: Set[str]= {func_declarator1, func_declarator2, func_declarator3, func_declarator4,
                           func_declarator5, func_declarator6, func_declarator7, func_declarator8,
                           func_declarator9, func_declarator10}
    test_callsite_sim(icallsite, func_names, test_sim)