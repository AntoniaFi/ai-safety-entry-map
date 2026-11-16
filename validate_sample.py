"""Draw a random validation sample and print what a human labeller needs (abstract + method excerpts), without the rule's answer.
Usage: python3 validate_sample.py [n] [seed]"""
import gzip, json, os, random, re, sys, importlib
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "data")
m4 = importlib.import_module("04_methods")
n = int(sys.argv[1]) if len(sys.argv) > 1 else 40; seed = int(sys.argv[2]) if len(sys.argv) > 2 else 11
P = {p["ax"]: p for p in json.load(open(os.path.join(DATA, "corpus.json")))["papers"] if p["ax"]}
pool = sorted(a for a in json.load(open(os.path.join(DATA, "fulltext_sample.json"))) if a in P and os.path.getsize(os.path.join(DATA, "html", a + ".html.gz")) > 20000)
random.seed(seed); ids = random.sample(pool, n)
json.dump(ids, open(os.path.join(DATA, "validation_ids.json"), "w"))
KEY = re.compile(r"(GPU|A100|H100|fine-?tun|LoRA|we train|trained on|participants|we recruit|API|open-source models|open-weight|parameters|activations|sparse autoencoder|theorem|we prove|we evaluate \w+ models)", re.I)
for i, ax in enumerate(ids):
    d = m4.parse(gzip.open(os.path.join(DATA, "html", ax + ".html.gz")).read().decode("utf8", "ignore"))
    sents = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", d["text"]))
    body = sents[len(sents) // 6:]
    ev = [s for s in body if KEY.search(s) and 50 < len(s) < 260]
    random.seed(ax); ev = random.sample(ev, min(5, len(ev)))
    print(f"\n[{i}] {ax} | {P[ax]['t']}\n  ABS: {P[ax]['ab'][:600]}")
    for s in ev: print("   -", s.replace("MATH", "[eq]"))
    print(f"   (display equations: {d['n_eq']}, theorem blocks: {d['n_thm']}, words: {len(d['text'].split())})")
