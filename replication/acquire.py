"""Download public sources; keep copyrighted full papers in ignored .cache."""
from pathlib import Path
import hashlib
import json
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def fetch(url, path):
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Academic research replication/1.0"})
                with urllib.request.urlopen(req, timeout=90) as response:
                    data = response.read()
                path.write_bytes(data)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2)
    return {"url": url, "path": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size, "retrieved": "2026-10-21"}


if __name__ == "__main__":
    sources = {
        "growiec_prettner": ("https://arxiv.org/pdf/2503.07341", ".cache/literature/growiec_prettner.pdf"),
        "jones": ("https://web.stanford.edu/~chadj/existentialrisk.pdf", ".cache/literature/jones.pdf"),
        "race": ("https://bpb-us-w2.wpmucdn.com/voices.uchicago.edu/dist/c/1708/files/2026/05/agi_race_post.pdf", ".cache/literature/race.pdf"),
        "rsi": ("https://raw.githubusercontent.com/elasticity-ai/elasticity/main/paper/elasticity-rsi-paper.pdf", ".cache/literature/rsi.pdf"),
        "armstrong": ("https://nickbostrom.com/papers/racing-to-the-precipice.pdf", ".cache/literature/armstrong.pdf"),
        "epoch_models": ("https://epoch.ai/data/all_ai_models.csv", "data/raw/epoch_models.csv"),
        "hf_meta": ("https://huggingface.co/api/datasets/lmarena-ai/arena-human-preference-140k/tree/main?recursive=true", ".cache/arena_tree.json"),
        "epoch_eci_page": ("https://epoch.ai/eci", ".cache/eci.html"),
        "training_repo": ("https://api.github.com/repos/epoch-research/training-cost-trends/git/trees/main?recursive=1", ".cache/training_tree.json"),
    }
    manifest = {}
    for name, (url, path) in sources.items():
        try:
            manifest[name] = fetch(url, path)
            print(name, manifest[name]["bytes"], flush=True)
        except Exception as error:
            manifest[name] = {"url": url, "error": str(error)}
            print(name, str(error), flush=True)
    (ROOT / "data/source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    import fitz
    for path in (ROOT / ".cache/literature").glob("*.pdf"):
        try:
            with fitz.open(path) as doc:
                path.with_suffix(".txt").write_text("\n".join(page.get_text() for page in doc), encoding="utf-8")
                print(path.stem, "pages", len(doc))
        except Exception as error:
            print(path.name, error)
