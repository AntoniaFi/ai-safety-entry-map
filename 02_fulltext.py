"""Step 2: download the arXiv HTML full text of a sample of core papers (data/html/<arxiv id>.html.gz).

Sample: per topic at most CAP core papers (half most cited, half random), all papers of the focus topics
(including peripheral ones). arxiv.org/html first, ar5iv as fallback. One request every 2 s. Resumable.
"""
import gzip, json, os, random, sys, time, urllib.request, collections
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "data"); OUT = os.path.join(DATA, "html")
os.makedirs(OUT, exist_ok=True)
CAP = 80
FOCUS = {"emergent-misalignment", "personas", "model-organisms", "evaluation-awareness", "sandbagging", "scheming-deception",
         "sycophancy", "personality-psychometrics", "introspection-selfknowledge", "cot-monitoring", "values-preferences"}
UA = {"User-Agent": "research-script/0.1"}

def sample():
    P = json.load(open(os.path.join(DATA, "corpus.json")))["papers"]
    random.seed(7); by = collections.defaultdict(list); pick = {}
    for p in P:
        if not p["ax"]: continue
        k = p["tp"][0]; core = p["tps"][k] >= 2
        if core: by[k].append(p)
        elif k in {"emergent-misalignment", "model-organisms", "evaluation-awareness", "sandbagging", "scheming-deception"}:
            pick[p["ax"]] = p
    for k, L in by.items():
        if k in FOCUS and len(L) <= 300 or len(L) <= CAP: S = L
        else:
            L.sort(key=lambda p: -p["c"]); S = L[:CAP // 2] + random.sample(L[CAP // 2:], CAP // 2)
        for p in S: pick[p["ax"]] = p
    return pick

def fetch(ax):
    for url in (f"https://arxiv.org/html/{ax}", f"https://ar5iv.labs.arxiv.org/html/{ax}"):
        try:
            b = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
            if b"ltx_document" in b or b"ltx_page_main" in b: return b
        except Exception as e:
            if getattr(e, "code", 0) == 429: time.sleep(60)
        time.sleep(1)
    return b""

if __name__ == "__main__":
    pick = sample(); json.dump(sorted(pick), open(os.path.join(DATA, "fulltext_sample.json"), "w"))
    todo = [a for a in pick if not os.path.exists(os.path.join(OUT, a + ".html.gz"))]
    print("sample", len(pick), "to fetch", len(todo), flush=True)
    if len(sys.argv) > 1 and sys.argv[1] == "reverse": todo.reverse()   # a second worker can run from the other end
    for i, ax in enumerate(todo):
        if os.path.exists(os.path.join(OUT, ax + ".html.gz")): continue
        b = fetch(ax)
        gzip.open(os.path.join(OUT, ax + ".html.gz"), "wb").write(b)   # empty file = no HTML version
        if i % 50 == 0: print(i, ax, len(b), flush=True)
        time.sleep(1)
    print("done", flush=True)
