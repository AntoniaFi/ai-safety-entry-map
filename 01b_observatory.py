"""Step 1b (23 Nov 2026): add papers from the AI Safety Observatory's Sources log to data/corpus.json.

Takes every Sources-log record (../AI_Safety_Observatory/content/sources/<year>.json, read only) with an arXiv id, dated
2022 or later, not yet read in full (data/methods.json) and not labelled "outside" (out of scope) in labels-v2.json.
Each is assigned to the 30 areas from title + abstract (taxonomy.assign; abstract from data/universe.sqlite). Unlike step 1,
a score of 1 is enough: the Observatory has already judged these records to be AI-safety research. They carry obs=1, and
step 2 (02_fulltext.py extra) downloads all of them. Existing corpus papers are kept; a paper already in the corpus is only marked.
Run after 01_corpus_store.py (which rebuilds corpus.json from scratch).
"""
import collections, glob, json, os, sqlite3, sys
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "data")
SRC = os.path.join(HERE, "..", "AI_Safety_Observatory", "content", "sources")
from taxonomy import assign

def candidates():
    lab = json.load(open(os.path.join(SRC, "labels-v2.json")))["records"]
    done = json.load(open(os.path.join(DATA, "methods.json")))
    recs = {}
    for fn in sorted(glob.glob(os.path.join(SRC, "[0-9]*.json"))):
        for r in json.load(open(fn)):
            if r.get("ax") and (r.get("d") or "")[:4] >= "2022": recs.setdefault(r["ax"], r)
    out = {}
    for ax, r in recs.items():
        if ax in done: continue
        l = lab.get(r["id"]) or lab.get("arxiv:" + ax) or {}
        if l.get("sc") == "outside": continue
        out[ax] = r
    return out

def main():
    cand = candidates()
    db = sqlite3.connect(f"file:{os.path.join(DATA, 'universe.sqlite')}?mode=ro", uri=True)
    cols = "wid, arxiv, doi, openalex, title, abstract, date, year, venue, authors, cites, src"
    fn = os.path.join(DATA, "corpus.json"); C = json.load(open(fn)); by_ax = {p["ax"]: p for p in C["papers"] if p["ax"]}
    added = collections.Counter(); marked = 0; none = 0; noab = 0
    for ax, r in sorted(cand.items()):
        row = db.execute(f"SELECT {cols} FROM works WHERE arxiv=?", (ax,)).fetchone()
        w = dict(zip([c.strip() for c in cols.split(",")], row)) if row else {}
        title = w.get("title") or r["t"]; ab = w.get("abstract") or ""
        if not ab: noab += 1
        tp = assign(title, ab)
        if not tp or max(tp.values()) < 1: none += 1; continue
        ranked = sorted(tp, key=lambda k: -tp[k])[:3]
        if ax in by_ax:
            by_ax[ax]["obs"] = 1; marked += 1; added[ranked[0]] += 1; continue
        try: au = json.loads(w["authors"]) if w.get("authors") else r.get("a") or []
        except Exception: au = r.get("a") or []
        p = dict(id=f"w{w['wid']}" if w else "obs-" + ax, t=title, ab=ab, y=w.get("year") or int(r["d"][:4]), d=w.get("date") or r["d"],
                 ax=ax, doi=w.get("doi") or r.get("doi"), oa=w.get("openalex"), c=w.get("cites") or r.get("c") or 0, v=w.get("venue") or r.get("v") or "",
                 f=[], au=[[None, a] for a in au if isinstance(a, str)], tp=ranked, tps={k: tp[k] for k in ranked},
                 src=sorted(set((w.get("src") or "").split(",")) - {""} | {"observatory"}), obs=1)
        C["papers"].append(p); by_ax[ax] = p; added[ranked[0]] += 1
    C["observatory_added"] = sum(added.values()) - marked; C["observatory_marked"] = marked
    json.dump(C, open(fn, "w"))
    print("candidates", len(cand), "kept (score >= 1)", sum(added.values()), "of which already in corpus", marked,
          "fit no area", none, "no abstract (title only)", noab)
    for k, n in added.most_common(): print(f"  {n:4d} {k}")

if __name__ == "__main__":
    main()
