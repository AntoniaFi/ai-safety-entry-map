"""Hand labels for the AI-safety classifier (the `gold` table), and the error rates that follow from them.

  python3 gold.py sample 120 [batch]   draw a sample spread over score bands, print title + abstract start, remember the ids
  python3 gold.py save labels.json [who] store hand labels {wid: 1 | 0} for the last sample (1 = AI safety under ETO's definition)
  python3 gold.py eval                  precision and recall at every threshold, weighted back to the whole store; writes data/threshold.json

Definition used when labelling (ETO): research on making AI systems do what they are meant to do with few adverse side effects in
real conditions: robustness, explainability, reward specification and alignment, reducing unwanted bias, monitoring and control,
testing and verification, human-AI and multi-agent coordination, deployment-context interventions. Not: AI used for the safety
of something else, most privacy-preserving ML, purely normative ethics, policy research, papers whose only point is a benchmark gain.
"""
import collections, json, os, random, sys, time
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
    random.shuffle(pick); pick = pick[:n]; inv = {w: k for k in S for w in S[k]}
    cnt = collections.Counter(inv[w] for w in pick)
    json.dump({"batch": batch, "ids": pick, "note": {str(w): {"stratum": list(inv[w]), "weight": len(S[inv[w]]) / cnt[inv[w]]} for w in pick}}, open(os.path.join(DATA, "gold_batch.json"), "w"))
    for i, wid in enumerate(pick):
        t, a, y, v = c.execute("SELECT title, abstract, year, venue FROM works WHERE wid=?", (wid,)).fetchone()
        print(f"[{wid}] ({y}, {(v or '')[:40]}) {t}\n    {(a or '')[:int(os.environ.get('ABS', 420))]}\n")

def save(fn, who):
    c = connect(); b = json.load(open(os.path.join(DATA, "gold_batch.json"))); L = json.load(open(fn))
    for wid, v in L.items():
        c.execute("INSERT OR REPLACE INTO gold(wid,safety,note,who,at,batch) VALUES(?,?,?,?,?,?)", (int(wid), int(v), json.dumps(b["note"][str(wid)]), who, time.strftime("%Y-%m-%d"), b["batch"]))
    c.commit(); print("gold labels in store:", c.execute("SELECT count(*), sum(safety) FROM gold").fetchone())

def evaluate():
    """Each gold record stands for `weight` records of the stratum it was drawn from (fixed when it was sampled), so the
    estimates stay valid when the classifier changes afterwards."""
    c = connect()
    rows = [(y, s, json.loads(lf), saf, json.loads(note)["weight"], batch) for y, s, lf, saf, note, batch in
            c.execute("SELECT g.safety, l.score, l.lf, l.safety, g.note, g.batch FROM gold g JOIN labels l USING(wid) WHERE g.note IS NOT NULL")]
    def est(pred, sel=lambda b: True):
        tp = fp = fn = 0.0; k = 0
        for y, s, lf, saf, w, batch in rows:
            if not sel(batch): continue
            k += 1; p_ = pred(s, lf, saf); tp += w * (p_ and y == 1); fp += w * (p_ and y == 0); fn += w * ((not p_) and y == 1)
        p = tp / (tp + fp) if tp + fp else 0; r = tp / (tp + fn) if tp + fn else 0
        nb = len({bt for *_, bt in rows if sel(bt)}) or 1          # every batch stands for the whole store once
        return dict(n=k, precision=round(p, 3), recall=round(r, 3), f1=round(2 * p * r / (p + r), 3) if p + r else 0, flagged=round((tp + fp) / nb), true_in_store=round((tp + fn) / nb))
    batches = sorted({r[5] for r in rows}); out = {"current": est(lambda s, lf, saf: saf == 1)}
    print("gold labels:", len(rows), "batches", batches); print("current rule, all gold:", out["current"])
    for b in batches:
        out[b] = est(lambda s, lf, saf: saf == 1, lambda x, b=b: x == b); print("  batch", b, out[b])
    table = []
    for t in (.5, .6, .7, .8, .9, .95):
        e = est(lambda s, lf, saf, t=t: lf["ai"] and lf["abs"] and not lf["domain"] and ((lf["rule"] == 1 and s >= t / 2) or s >= t)); e["threshold"] = t; table.append(e); print("   ", e)
    out["table"] = table
    out["note"] = "Weighted back from samples spread over score bands. One labeller (Claude) unless the gold table says otherwise. ETO reports precision 0.73 and recall 0.80 for its classifier."
    b = c.execute("SELECT count(*), sum(l.safety) FROM works w JOIN labels l USING(wid) WHERE json_extract(w.topics,'$.iasr_cited') IS NOT NULL AND w.year>=2018 AND length(w.abstract)>200").fetchone()
    out["iasr_cited"] = {"with_abstract": b[0], "flagged": b[1]}; print("works cited by the International AI Safety Report (2018 on, with abstract):", b[0], "flagged:", b[1])
    json.dump(out, open(os.path.join(DATA, "gold_eval.json"), "w"), indent=1)

import collections
if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "sample": sample(int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else time.strftime("b%m%d%H%M"))
    elif cmd == "save": save(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "Claude")
    elif cmd == "eval": evaluate()
