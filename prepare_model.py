"""Download the embedding model once, then initialize an empty local library."""

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent
for key, value in {
    "TEMP": ROOT / "tmp",
    "TMP": ROOT / "tmp",
    "HF_HOME": ROOT / "cache" / "huggingface",
    "XDG_CACHE_HOME": ROOT / "cache",
    "FASTEMBED_CACHE_PATH": ROOT / "models",
}.items():
    Path(value).mkdir(parents=True, exist_ok=True)
    os.environ[key] = str(value)

os.environ.pop("HF_HUB_OFFLINE", None)
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

from fastembed import TextEmbedding


model = TextEmbedding(
    "BAAI/bge-small-zh-v1.5",
    cache_dir=str(ROOT / "models"),
    local_files_only=False,
    threads=2,
)
next(iter(model.embed(["local knowledge base ready"])))

os.environ["HF_HUB_OFFLINE"] = "1"
import knowledge

knowledge.init()
print(f"Model and empty library are ready under {ROOT}")
