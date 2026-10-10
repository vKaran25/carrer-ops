"""Local ONNX embeddings; no resume text sent to an embedding API."""

from functools import lru_cache
from threading import Lock

import numpy as np

from app.config import get_settings

_lock = Lock()


@lru_cache(maxsize=1)
def model():
    from fastembed import TextEmbedding
    return TextEmbedding(model_name=get_settings().embedding_model, cache_dir="./data/embedding-cache", threads=2)


@lru_cache(maxsize=4096)
def vector(text: str) -> tuple[float, ...]:
    with _lock:
        value = next(iter(model().embed([text[:24000]])))
    norm = np.linalg.norm(value)
    return tuple((value / norm if norm else value).tolist())


def similarity(left: str, right: str) -> float:
    if not left.strip() or not right.strip():
        return 0.0
    return float(np.clip(np.dot(vector(left), vector(right)), 0, 1))
