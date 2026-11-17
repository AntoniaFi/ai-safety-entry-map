"""Hand labels for the AI-safety classifier (the `gold` table), and the error rates that follow from them.

  python3 gold.py sample 120 [batch]   draw a sample spread over score bands, print title + abstract start, remember the ids
  python3 gold.py save labels.json [who] store hand labels {wid: 1 | 0} for the last sample (1 = AI safety under ETO's definition)
  python3 gold.py eval                  precision and recall at every threshold, weighted back to the whole store; writes data/threshold.json

Definition used when labelling (ETO): research on making AI systems do what they are meant to do with few adverse side effects in
real conditions: robustness, explainability, reward specification and alignment, reducing unwanted bias, monitoring and control,
testing and verification, human-AI and multi-agent coordination, deployment-context interventions. Not: AI used for the safety
of something else, most privacy-preserving ML, purely normative ethics, policy research, papers whose only point is a benchmark gain.
"""
import json, os, random, sys, time
from store import connect, DATA
BANDS = [(0, .2), (.2, .5), (.5, .8), (.8, .95), (.95, 1.01)]

def band(s): return next(i for i, (a, b) in enumerate(BANDS) if a <= s < b)

def strata(c):
    S = {}
    for wid, score, lf in c.execute("SELECT l.wid, l.score, l.lf FROM labels l JOIN works w USING(wid) WHERE length(w.abstract)>200 AND json_extract(l.lf,'$.ai')=1"):
        S.setdefault((band(score), json.loads(lf)["rule"]), []).append(wid)
    return S

def sample(n, batch):
    c = connect(); S = strata(c); done = {r[0] for r in c.execute("SELECT wid FROM gold")}
    random.seed(hash(batch) % 10000); per = max(3, n // len(S)); pick = []
    for k in sorted(S, key=str):
        pool = [w for w in S[k] if w not in done]; pick += random.sample(pool, min(per, len(pool)))
    random.shuffle(pick); pick = pick[:n]
    json.dump({"batch": batch, "ids": pick}, open(os.path.join(DATA, "gold_batch.json"), "w"))
    for i, wid in enumerate(pick):
        t, a, y, v = c.execute("SELECT title, abstract, year, venue FROM works WHERE wid=?", (wid,)).fetchone()
        print(f"[{wid}] ({y}, {(v or '')[:40]}) {t}\n    {(a or '')[:int(os.environ.get('ABS', 420))]}\n")

def save(fn, who):
    c = connect(); b = json.load(open(os.path.join(DATA, "gold_batch.json"))); L = json.load(open(fn))
    for wid, v in L.items():
        c.execute("INSERT OR REPLACE INTO gold(wid,safety,note,who,at,batch) VALUES(?,?,?,?,?,?)", (int(wid), int(v), None, who, time.strftime("%Y-%m-%d"), b["batch"]))
    c.commit(); print("gold labels in store:", c.execute("SELECT count(*), sum(safety) FROM gold").fetchone())

def evaluate():
    c = connect(); S = strata(c); size = {k: len(v) for k, v in S.items()}
    G = collections.defaultdict(list)
    for wid, y, score, lf, saf in c.execute("SELECT g.wid, g.safety, l.score, l.lf, l.safety FROM gold g JOIN labels l USING(wid)"):
        G[(band(score), json.loads(lf)["rule"])].append((y, score, json.loads(lf)["rule"], saf))
    n = sum(len(v) for v in G.values()); print("gold labels:", n, "in", len(G), "of", len(S), "strata")
    def est(thr):
        tp = fp = fn = 0.0
        for k, rows in G.items():
            w = size[k] / len(rows)
            for y, s, rule, _ in rows:
                pred = rule == 1 or s >= thr
                tp += w * (pred and y == 1); fp += w * (pred and y == 0); fn += w * ((not pred) and y == 1)
        p = tp / (tp + fp) if tp + fp else 0; r = tp / (tp + fn) if tp + fn else 0
        return dict(threshold=thr, precision=round(p, 3), recall=round(r, 3), f1=round(2 * p * r / (p + r), 3) if p + r else 0, flagged=round(tp + fp), true_in_store=round(tp + fn))
    rows = [est(t) for t in (.5, .6, .7, .8, .85, .9, .95, .98, 1.01)]
    for r in rows: print("  ", r)
    ok = [r for r in rows if r["precision"] >= 0.70] or rows
    best = max(ok, key=lambda r: r["f1"]); best["gold_n"] = n; best["table"] = rows
    best["note"] = "Weighted back from a sample spread over score bands; one labeller (Claude) unless the gold table says otherwise. ETO reports precision 0.73, recall 0.80 for its classifier."
    json.dump(best, open(os.path.join(DATA, "threshold.json"), "w"), indent=1); print("chosen:", {k: best[k] for k in ("threshold", "precision", "recall", "f1", "flagged", "true_in_store")})
    # independent benchmark: works cited by the International AI Safety Report (from the Observatory log)
    b = c.execute("SELECT count(*), sum(l.safety) FROM works w JOIN labels l USING(wid) WHERE json_extract(w.topics,'$.iasr_cited') IS NOT NULL AND w.year>=2018 AND length(w.abstract)>200").fetchone()
    print("IASR-cited works with an abstract:", b[0], "flagged as safety:", b[1])

import collections
if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "sample": sample(int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else time.strftime("b%m%d%H%M"))
    elif cmd == "save": save(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "Claude")
    elif cmd == "eval": evaluate()
