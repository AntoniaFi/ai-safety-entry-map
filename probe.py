"""Count how many full texts of a topic mention a pattern (in the body, references cut). Usage: python3 probe.py <topic,topic> <regex> [min_hits]"""
import gzip, json, os, re, sys, importlib
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "data")
m4 = importlib.import_module("04_methods")
topics = set(sys.argv[1].split(",")); rx = re.compile(sys.argv[2], re.I); mn = int(sys.argv[3]) if len(sys.argv) > 3 else 1
P = [p for p in json.load(open(os.path.join(DATA, "corpus.json")))["papers"] if p["ax"] and p["tp"][0] in topics and p["tps"][p["tp"][0]] >= 2]
tot = 0; hits = []
for p in P:
    fn = os.path.join(DATA, "html", p["ax"] + ".html.gz")
    if not os.path.exists(fn) or os.path.getsize(fn) < 20000: continue
    cache = os.path.join(DATA, "text", p["ax"] + ".txt"); os.makedirs(os.path.dirname(cache), exist_ok=True)
    if os.path.exists(cache): t = open(cache).read()
    else:
        t = m4.parse(gzip.open(fn).read().decode("utf8", "ignore"))["text"]; open(cache, "w").write(t)
    tot += 1; f = [m for m in rx.finditer(t)]
    if len(f) >= mn:
        m = f[0]; hits.append((len(f), p["ax"], p["t"][:70], re.sub(r"\s+", " ", t[max(0, m.start() - 110):m.end() + 130])))
hits.sort(reverse=True)
print(f"{len(hits)} of {tot} papers ({100 * len(hits) / max(1, tot):.0f}%) mention /{sys.argv[2]}/ at least {mn}x")
for n, ax, ti, ctx in hits[:int(os.environ.get('SHOW', 8))]: print(f"  [{ax}] x{n} {ti}\n      …{ctx}…")
