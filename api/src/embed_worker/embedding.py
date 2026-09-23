import json

import numpy as np
import onnxruntime
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer


def passage_input(title, heading_path, text):
    head = " › ".join(p for p in [title, heading_path] if p)
    if head:
        return f"passage: {head}\n{text}"
    return f"passage: {text}"


def query_input(text):
    return f"query: {text}"


POST_CHARS = 1200


def post_input(title, text):
    body = "\n".join(p for p in [title, text] if p)[:POST_CHARS]
    return f"passage: {body}"


class Embedder:
    def __init__(self, model_id):
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
        self.session = onnxruntime.InferenceSession(
            model_path, options, providers=["CPUExecutionProvider"]
        )
        self.input_names = {i.name for i in self.session.get_inputs()}
        output_names = [o.name for o in self.session.get_outputs()]
        self.output_name = (
            "last_hidden_state" if "last_hidden_state" in output_names else output_names[0]
        )

    def embed(self, texts):
        encodings = self.tokenizer.encode_batch(texts)
        input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
        feeds = {"input_ids": input_ids, "attention_mask": attention_mask}
        if "token_type_ids" in self.input_names:
            feeds["token_type_ids"] = np.zeros_like(input_ids)

        hidden = self.session.run([self.output_name], feeds)[0]
        mask = attention_mask[:, :, np.newaxis].astype(hidden.dtype)
        pooled = (hidden * mask).sum(axis=1) / np.clip(mask.sum(axis=1), 1e-9, None)
        norms = np.linalg.norm(pooled, axis=1, keepdims=True)
        normalized = pooled / np.clip(norms, 1e-12, None)
        return [row.tolist() for row in normalized.astype(np.float32)]
