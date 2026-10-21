"""Freeze public numeric data, excluding Arena prompts and personal identifiers."""
from pathlib import Path
import hashlib
import io
import json
import re
import requests
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
RAW.mkdir(parents=True, exist_ok=True)
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Academic research replication/1.0"


def get(url):
    response = SESSION.get(url, timeout=(15, 60))
    response.raise_for_status()
    return response


def save(url, name):
    path = RAW / name
    if not path.exists():
        path.write_bytes(get(url).content)
    return {"url": url, "path": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "retrieved": "2026-10-21"}


class RangeFile(io.RawIOBase):
    """Read Parquet columns over HTTPS without downloading conversation columns."""
    def __init__(self, url, size):
        self.url, self.size, self.pos = url, size, 0

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos

    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else (self.pos if whence == 1 else self.size) + offset
        return self.pos

    def read(self, size=-1):
        if size < 0:
            size = self.size - self.pos
        size = min(size, self.size - self.pos)
        if size <= 0: return b""
        end = self.pos + size - 1
        response = SESSION.get(self.url + f"?download=true&range_start={self.pos}",
                               headers={"Range": f"bytes={self.pos}-{end}"}, timeout=(15, 60))
        response.raise_for_status()
        if response.status_code != 206 or len(response.content) != size:
            raise IOError(f"Server did not honor byte range: {response.status_code}, {len(response.content)}, expected {size}")
        self.pos += size
        return response.content


def arena():
    path = RAW / "arena_numeric.parquet"
    if path.exists():
        manifest_path=ROOT/'data/data_manifest.json'
        entry=json.loads(manifest_path.read_text())['arena'] if manifest_path.exists() else None
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if not entry or not entry.get('revision') or entry.get('sha256')!=digest:
            raise ValueError('Cached Arena bytes need their original immutable revision and matching hash; do not relabel them from a live API.')
        return entry
    info = get("https://huggingface.co/api/datasets/lmarena-ai/arena-human-preference-140k").json()
    revision = info["sha"]
    tree = get(f"https://huggingface.co/api/datasets/lmarena-ai/arena-human-preference-140k/tree/{revision}?recursive=true").json()
    files = [f for f in tree if f["path"].endswith(".parquet")]
    columns = ["model_a", "model_b", "winner", "evaluation_order", "language", "is_code", "timestamp"]
    frames = []
    if not path.exists():
        for f in files:
            url = f"https://huggingface.co/datasets/lmarena-ai/arena-human-preference-140k/resolve/{revision}/{f['path']}"
            remote = RangeFile(url, f["size"])
            table = pq.ParquetFile(remote).read(columns=columns)
            frames.append(table.to_pandas())
            print(f["path"], len(frames[-1]), flush=True)
        pd.concat(frames, ignore_index=True).to_parquet(path, index=False)
    return {"url": "https://huggingface.co/datasets/lmarena-ai/arena-human-preference-140k", "revision": revision,
            "path": str(path.relative_to(ROOT)), "columns": columns, "license": "CC-BY-4.0",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "retrieved": "2026-10-21"}


if __name__ == "__main__":
    manifest_path = ROOT / "data/data_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    tasks = {
        "epoch_models": lambda: save("https://epoch.ai/data/all_ai_models.csv", "epoch_models.csv"),
        "arena": arena,
    }
    for name, task in tasks.items():
        try:
            manifest[name] = task()
            print(name, "complete", flush=True)
        except Exception as e:
            if name not in manifest:manifest[name] = {"error": str(e)}
            print(name, str(e), flush=True)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    for url, name in [("https://epoch.ai/benchmarks/use-this-data", "epoch_download_page.html"),
                      ("https://epoch.ai/eci", "eci.html")]:
        html = get(url).text
        (ROOT / ".cache" / name).write_text(html, encoding="utf-8")
        print(name, sorted(set(re.findall(r'[^\s"<>]*(?:\.csv|\.zip|\.json)[^\s"<>]*', html)))[:30])
