"""Build a park knowledge base (animals + attractions) from a local public crawl.

Reads pages.json + raw HTML from KOLMARDEN_SCRAPE_DIR and writes data/generated/kb.json.
The generated file is gitignored: the source text belongs to the park, so the public repo
ships only this script, and each record keeps its source URL for attribution.
"""
import html, json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(os.environ.get("KOLMARDEN_SCRAPE_DIR", ROOT.parent / "kolmarden-scrape" / "out"))
OUT = ROOT / "data" / "generated" / "kb.json"

def raw_path(rec):
    return SRC / "raw" / re.split(r"[\\/]", rec["rawFile"])[-1]

def clean(s):
    s = re.sub(r"<(script|style)\b.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

def first(pattern, s):
    m = re.search(pattern, s, flags=re.S)
    return clean(m.group(1)) if m else None

def parse(rec, kind):
    s = raw_path(rec).read_text(encoding="utf8", errors="ignore")
    body = clean(s)
    # Drop the shared site header/footer boilerplate around the main content.
    body = re.sub(r"^.*?Visa på karta\s*", "", body)
    body = re.split(r"Äventyret väntar|Frågor & svar Tillgänglighet", body)[0].strip()
    item = {
        "id": rec["url"].rstrip("/").rsplit("/", 1)[-1],
        "kind": kind,
        "name": first(r"<h1[^>]*>(.*?)</h1>", s) or rec.get("title"),
        "headings": [clean(h) for h in re.findall(r"<h[23][^>]*>(.*?)</h[23]>", s, flags=re.S)][:16],
        "text_sv": body[:6000],
        "image": (re.search(r'og:image" content="([^"]+)"', s) or [None, None])[1],
        "source_url": rec["url"],
    }
    sci = re.search(r"\b([A-Z][a-z]+ [a-z]+(?: [a-z]+)?)\b", body[:300])
    if kind == "animal" and sci:
        item["scientific_name"] = sci.group(1)
    geo = re.search(r"mlat=([0-9.]+)&(?:amp;)?mlon=([0-9.]+)", s)
    if geo:
        item["lat"], item["lon"] = float(geo.group(1)), float(geo.group(2))
    elif item["id"] in HAND_PINS:  # pages without a map link
        item["lat"], item["lon"] = HAND_PINS[item["id"]]
    h = re.search(r"Längdkrav:\s*([^:]*?\d+\s*cm[^A-ZÅÄÖ]*)", body)
    if h:
        item["height_requirement"] = h.group(1).strip()
        nums = [int(n) for n in re.findall(r"(\d+)\s*cm", h.group(1))]
        if nums:
            item["min_height_cm"] = min(nums)
    return item

# Places whose page has no map link; pinned by hand next to the ride that serves them.
HAND_PINS = {"delfin": (58.6614, 16.4467)}  # dolphinarium, by Delfinexpressen


def main():
    pages = json.loads((SRC / "pages.json").read_text(encoding="utf8"))
    kinds = {"/djurpark/djur/": "animal", "/parken/attraktioner/": "attraction"}
    items, seen = [], set()
    for rec in pages:
        if rec.get("status") != 200:
            continue
        for marker, kind in kinds.items():
            tail = rec["url"].split(marker)
            if len(tail) == 2 and tail[1].strip("/") and rec["url"] not in seen:
                seen.add(rec["url"])
                try:
                    items.append(parse(rec, kind))
                except FileNotFoundError:
                    print("missing raw file for", rec["url"], file=sys.stderr)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"park": "Kolmården", "items": items}, ensure_ascii=False, indent=1), encoding="utf8")
    n = {k: sum(i["kind"] == k for i in items) for k in kinds.values()}
    print(f"wrote {OUT.relative_to(ROOT)}: {n}")

if __name__ == "__main__":
    main()
