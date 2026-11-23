"""Gold sample C (23 Nov 2026): Claude's reading of the methods sections vs the rules, for all five skills.

  python3 validate_gold_C.py sample [n] [seed]   draw n papers read in full, stratified by area (proportional, at least 3 per area)
                                                 -> data/validation_ids_C.json
  python3 validate_gold_C.py show <from> <to>     print what the labeller reads: abstract, section headings, the methods sections
                                                 (up to ~700 words) and sentences on hardware, models and participants; never the rule's answer
  python3 validate_gold_C.py compare             data/gold_C_labels.json vs the rules -> data/validation.json (shown on the Method tab)

Labels use the level definitions on the page (site/template.html, const LV): coding c 0-3, working with ML models e 0-4,
maths m 0-3, compute k 0-5, studies with people h 0/1.
"""
import collections, gzip, importlib, json, os, random, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "data")
sys.path.insert(0, HERE)
IDS = os.path.join(DATA, "validation_ids_C.json"); GOLD = os.path.join(DATA, "gold_C_labels.json")
SKILLS = [("c", "Coding", 3), ("e", "Working with ML models", 4), ("m", "Maths", 3), ("k", "Compute", 5), ("h", "Studies with people", 1)]

def corpus():
    return {p["ax"]: p for p in json.load(open(os.path.join(DATA, "corpus.json")))["papers"] if p["ax"]}

def sample(n, seed):
    P = corpus(); M = json.load(open(os.path.join(DATA, "methods.json")))
    by = collections.defaultdict(list)
    for ax in sorted(M):
        p = P.get(ax)
        if p and (p["tps"][p["tp"][0]] >= 2 or p.get("obs")): by[p["tp"][0]].append(ax)
    tot = sum(len(v) for v in by.values())
    quota = {k: min(len(v), max(3, round(n * len(v) / tot))) for k, v in by.items()}
    while sum(quota.values()) > n:                         # trim the quotas furthest above their share, never below 3
        k = max((k for k in quota if quota[k] > 3), key=lambda k: quota[k] - n * len(by[k]) / tot); quota[k] -= 1
    while sum(quota.values()) < n:
        k = max((k for k in quota if quota[k] < len(by[k])), key=lambda k: n * len(by[k]) / tot - quota[k]); quota[k] += 1
    rnd = random.Random(seed); ids = []
    for k in sorted(by): ids += rnd.sample(by[k], min(quota[k], len(by[k])))
    rnd.shuffle(ids)
    json.dump(ids, open(IDS, "w"))
    print(len(ids), "papers;", {k: quota[k] for k in sorted(quota)})

METH = re.compile(r"method|experiment|setup|set-up|implementation|approach|study design|participants|procedure|training|fine-?tun|"
                  r"evaluation|models?\b|data|framework|benchmark|analysis|survey|interview|proof|theor", re.I)
SKIP = re.compile(r"introduction|related work|background|conclusion|discussion|limitation|acknowledg|abstract|keywords|impact statement|ethics", re.I)
HW = re.compile(r"(GPU|A100|H100|H200|V100|RTX|TPU|GPU[- ]hours|compute budget|\bAPI\b|LoRA|billion parameters|\d+\s?B\b|participants|recruited|Prolific|MTurk|"
                r"chat interface|ChatGPT|we (train|fine-?tune|pretrain)|from scratch|reinforcement learning|activations?|sparse autoencoder|theorem|we prove)", re.I)

def show(a, b):
    m4 = importlib.import_module("04_methods"); P = corpus(); ids = json.load(open(IDS))
    for i in range(a, min(b, len(ids))):
        ax = ids[i]; p = P[ax]
        d = m4.parse(gzip.open(os.path.join(DATA, "html", ax + ".html.gz")).read().decode("utf8", "ignore"))
        t = d["text"]; parts = re.split(r"\n## ", t); heads = [x.split("\n", 1)[0][:60] for x in parts[1:]]
        meth = []; words = 0
        for x in parts[1:]:
            h, _, body = x.partition("\n")
            if SKIP.search(h) or not METH.search(h) or h.lower().startswith("appendix") and words > 300: continue
            w = body.split()
            if len(w) < 15: continue
            take = w[:max(0, 700 - words)][:300]; meth.append(f"[{h[:60]}] " + " ".join(take)); words += len(take)
            if words >= 700: break
        sents = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", t)); seen = set(" ".join(meth)[:100000].split(". "))
        hw = [s for s in sents if HW.search(s) and 40 < len(s) < 300 and s not in seen]
        hw = [s[:220] for s in hw[:2] + random.Random(ax).sample(hw[2:], min(4, len(hw[2:])))]
        print(f"\n===== [{i}] {ax} | {p['t']}\nABS: {(p['ab'] or '')[:450]}\nHEADINGS: {' | '.join(h[:40] for h in heads[:22])}")
        print("METHODS:", " ".join(meth).replace("MATH", "[eq]")[:2600])
        print("OTHER:", " /// ".join(s.replace("MATH", "[eq]") for s in hw))
        print(f"(display equations {d['n_eq']}, theorem blocks {d['n_thm']}, proofs {d['n_proof']}, figures {d['n_fig']}, tables {d['n_tab']}, words {len(t.split())})")

def compare():
    A = importlib.import_module("05_aggregate")
    M = json.load(open(os.path.join(DATA, "methods.json"))); G = json.load(open(GOLD))["labels"]
    rule = {}
    for ax in G:
        m = M[ax]; code, ml = A.levels(m); rule[ax] = dict(c=code, e=ml, m=m["math"], k=m["compute"], h=int(m["human"]))
    res = {"n": len(G), "set": "C"}
    for k, name, top in SKILLS:
        pairs = [(G[ax][k], rule[ax][k]) for ax in G if G[ax].get(k) is not None]
        conf = collections.Counter((a, b) for a, b in pairs)
        res[k] = dict(n=len(pairs), exact=round(sum(a == b for a, b in pairs) / len(pairs), 3),
                      within1=round(sum(abs(a - b) <= 1 for a, b in pairs) / len(pairs), 3),
                      reach=round(sum((a <= t) == (b <= t) for a, b in pairs for t in range(top)) / (len(pairs) * top), 3),
                      bias=round(sum(b - a for a, b in pairs) / len(pairs), 2),
                      confusion=[[conf[(a, b)] for b in range(top + 1)] for a in range(top + 1)])
        print(f"{name:24s} n={len(pairs)} same {res[k]['exact']:.0%}  within one {res[k]['within1']:.0%}  reach {res[k]['reach']:.0%}  bias {res[k]['bias']:+}")
        for a in range(top + 1): print("    label", a, "rule:", res[k]["confusion"][a])
    res["note"] = (f"{len(G)} papers read in full, drawn at random within each area (in proportion to its size, at least 3 per area). "
                   "Claude read each paper's methods sections and its statements on models, hardware and participants and set the five levels "
                   "from the definitions on this page, without seeing the rule's answer. One labeller, not a person: a consistency check, not ground truth. "
                   "Reach decision: over every possible skill level, how often rule and label agree on whether the paper is within reach. "
                   "Bias: average of rule minus label (positive: the rule rates papers as harder).")
    old = json.load(open(os.path.join(DATA, "validation.json"))) if os.path.exists(os.path.join(DATA, "validation.json")) else {}
    if old.get("set") != "C": res["earlier"] = old                         # samples A and B (old scales), kept for the record
    else: res["earlier"] = old.get("earlier")
    json.dump(res, open(os.path.join(DATA, "validation.json"), "w"), indent=1)

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "sample": sample(int(sys.argv[2]) if len(sys.argv) > 2 else 200, int(sys.argv[3]) if len(sys.argv) > 3 else 23)
    elif cmd == "show": show(int(sys.argv[2]), int(sys.argv[3]))
    elif cmd == "compare": compare()
