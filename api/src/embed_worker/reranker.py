import json

import numpy as np
import onnxruntime
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer


class Reranker:
    def __init__(self, model_id, threads):
        model_path = hf_hub_download(model_id, "onnx/model_quantized.onnx")
        tokenizer_path = hf_hub_download(model_id, "tokenizer.json")
        config_path = hf_hub_download(model_id, "tokenizer_config.json")

        with open(config_path) as f:
            config = json.load(f)

        pad_token = config.get("pad_token", "<pad>")
        if isinstance(pad_token, dict):
            pad_token = pad_token.get("content", "<pad>")
        max_length = config.get("model_max_length") or 512
        if not isinstance(max_length, int) or max_length > 1_000_000:
            max_length = 512

        self.tokenizer = Tokenizer.from_file(tokenizer_path)
        pad_id = self.tokenizer.token_to_id(pad_token)
        self.tokenizer.enable_truncation(max_length=max_length)
        self.tokenizer.enable_padding(
            pad_id=pad_id if pad_id is not None else 0, pad_token=pad_token
        )

        options = onnxruntime.SessionOptions()
        options.enable_cpu_mem_arena = False
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        self.session = onnxruntime.InferenceSession(
            model_path, options, providers=["CPUExecutionProvider"]
        )
        self.input_names = {i.name for i in self.session.get_inputs()}
        self.output_name = self.session.get_outputs()[0].name

    def score(self, query, documents):
        if not documents:
            return []
        encodings = self.tokenizer.encode_batch([(query, d) for d in documents])
        input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
        feeds = {"input_ids": input_ids, "attention_mask": attention_mask}
        if "token_type_ids" in self.input_names:
            feeds["token_type_ids"] = np.array([e.type_ids for e in encodings], dtype=np.int64)

        logits = self.session.run([self.output_name], feeds)[0]
        logits = np.asarray(logits, dtype=np.float32).reshape(len(documents), -1)[:, -1]
        return [float(v) for v in 1.0 / (1.0 + np.exp(-logits))]
