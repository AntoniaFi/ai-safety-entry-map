"""Bring what already exists into the store: the Observatory sources log (content/sources/*.json, including LessWrong and
Alignment Forum posts, reports and Chinese works) and the Entry Map corpus (data/corpus.json, which has abstracts)."""
import glob, json, os
from store import connect, upsert
HERE = os.path.dirname(os.path.abspath(__file__))
c = connect(); n = new = 0
for f in sorted(glob.glob(os.path.join(HERE, "..", "..", "AI_Safety_Observatory", "content", "sources", "*.json"))):
    for it in json.load(open(f)):
        y = int(it["d"][:4]) if it.get("d") else None
        r = dict(arxiv=it.get("ax"), doi=it.get("doi"), lw=it.get("lw"), title=it.get("t"), date=it.get("d"), year=y, venue=it.get("v"), kind=it.get("k"),
                 authors=it.get("a"), cites=it.get("c") if it.get("k") != "post" else None, lang=it.get("l"),
                 topics={"observatory": it.get("tp"), "reliable": it.get("r"), "why": it.get("rw"), "iasr_cited": it.get("ic")} if (it.get("tp") or it.get("ic")) else None)
        n += 1; new += upsert(c, r, "observatory")[1]
    c.commit()
print("Observatory log:", n, "records,", new, "new")
n = new = 0
for p in json.load(open(os.path.join(HERE, "..", "data", "corpus.json")))["papers"]:
    r = dict(arxiv=p.get("ax"), doi=p.get("doi"), s2=p["id"], title=p["t"], abstract=p["ab"], date=p.get("d"), year=p.get("y"), venue=p.get("v") or None,
             authors=[a[1] for a in p["au"]], cites=p["c"])
    n += 1; new += upsert(c, r, "entrymap")[1]
c.commit(); print("Entry Map corpus:", n, "records,", new, "new")
print("works in store:", c.execute("SELECT count(*) FROM works").fetchone()[0])
