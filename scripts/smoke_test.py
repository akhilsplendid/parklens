"""Check the Meta Model API key works: list models, then one grounded chat call.

Run from the repo root:  python scripts/smoke_test.py
Needs MODEL_API_KEY in the environment or in .env. Standard library only.
"""
import json, os, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
env = ROOT / ".env"
if env.exists():
    for line in env.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

BASE = os.environ.get("MODEL_API_BASE", "https://api.meta.ai/v1")
KEY = os.environ["MODEL_API_KEY"]

def call(path, body=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

models = [m["id"] for m in call("/models")["data"]]
print("models:", ", ".join(models))

kb = ROOT / "data" / "generated" / "kb.json"
tiger = next(i for i in json.loads(kb.read_text(encoding="utf8"))["items"] if i["id"] == "tiger")
reply = call("/chat/completions", {
    "model": "muse-spark-1.3",
    "messages": [
        {"role": "system", "content": "You are a park guide. Answer only from the provided park text. Reply in English, 2 sentences, for a 7-year-old."},
        {"role": "user", "content": f"Park text:\n{tiger['text_sv'][:3000]}\n\nWhy are tigers special?"},
    ],
})
print("\nguide:", reply["choices"][0]["message"]["content"])
