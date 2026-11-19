"""Step 1 (since 19 Nov 2026): build the Entry Map corpus from the universe store (harvest/, data/universe.sqlite)
instead of the Semantic Scholar searches of 01_corpus.py.

Every record from FIRST_YEAR on with an abstract is assigned to the 30 areas from title + abstract (taxonomy.assign).
A paper counts for an area when its score there is at least 2 (title hit, or two abstract hits): the same "core" rule as before.
Records that are neither on arXiv nor cited at least MIN_CITES times are left out, as before (unreviewed, uncited).
Reads the store only. Output: data/corpus.json in the format the later steps expect (id = "w<store row id>").
"""
import json, multiprocessing, os, sqlite3, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "data")
from taxonomy import assign
FIRST_YEAR = 2022; MIN_CITES = 3

def one(row):
    wid, title, ab = row[0], row[1], row[2]
    tp = assign(title, ab)
    if not tp or max(tp.values()) < 2: return None
    return wid, tp

def main():
    db = sqlite3.connect(f"file:{os.path.join(DATA, 'universe.sqlite')}?mode=ro", uri=True)
    rows = db.execute("SELECT wid, title, abstract FROM works WHERE year >= ? AND year <= 2026 AND length(abstract) > 200 AND title IS NOT NULL", (FIRST_YEAR,)).fetchall()
    print("records with an abstract from", FIRST_YEAR, ":", len(rows), flush=True)
    with multiprocessing.Pool(8) as pool: hits = [h for h in pool.imap(one, rows, chunksize=4000) if h]
    print("in at least one area (score >= 2):", len(hits), flush=True)
    out = []; dropped = 0
    cols = "wid, arxiv, doi, openalex, s2, title, abstract, date, year, venue, kind, authors, cites, src, lang"
    for wid, tp in hits:
        r = dict(zip([c.strip() for c in cols.split(",")], db.execute(f"SELECT {cols} FROM works WHERE wid=?", (wid,)).fetchone()))
        if not r["arxiv"] and (r["cites"] or 0) < MIN_CITES: dropped += 1; continue
        if r["lang"] and r["lang"] not in ("en", None): continue
        ranked = sorted(tp, key=lambda k: -tp[k])
        try: au = json.loads(r["authors"]) if r["authors"] else []
        except Exception: au = []
        out.append(dict(id=f"w{wid}", t=r["title"], ab=r["abstract"], y=r["year"], d=r["date"], ax=r["arxiv"], doi=r["doi"], oa=r["openalex"],
                        c=r["cites"] or 0, v=r["venue"] or "", f=[], au=[[None, a] for a in au if isinstance(a, str)], tp=ranked[:3],
                        tps={k: tp[k] for k in ranked[:3]}, src=sorted((r["src"] or "").split(","))))
    print("dropped (not on arXiv and cited fewer than", MIN_CITES, "times):", dropped)
    json.dump(dict(papers=out, built_from="universe store", first_year=FIRST_YEAR, searched=len(rows), dropped_uncited=dropped), open(os.path.join(DATA, "corpus.json"), "w"))
    c = collections.Counter(p["tp"][0] for p in out)
    print("corpus", len(out), "on arXiv", sum(1 for p in out if p["ax"]))
    for k, n in c.most_common(): print(f"  {n:6d} {k}")

if __name__ == "__main__":
    main()
