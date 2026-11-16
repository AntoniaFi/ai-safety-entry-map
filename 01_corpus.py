"""Step 1: build the paper corpus.

Sources: (a) every arXiv record from 2022 on in the Observatory sources log, (b) Semantic Scholar bulk search for each
topic's phrases (2022 on). Semantic Scholar gives title, abstract, authors (with ids), fields of study, citations.
Papers are then assigned to topics from title + abstract (taxonomy.py). Output: data/corpus.json
Every request is cached in data/cache_s2/.
"""
import glob, hashlib, json, os, sys, time, urllib.parse, urllib.request
from taxonomy import T, assign

HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "data")
CACHE = os.path.join(DATA, "cache_s2"); os.makedirs(CACHE, exist_ok=True)
OBS = os.path.join(HERE, "..", "AI_Safety_Observatory", "content", "sources")
S2 = "https://api.semanticscholar.org/graph/v1"
FIELDS = "title,abstract,year,publicationDate,externalIds,citationCount,s2FieldsOfStudy,venue,publicationTypes,authors.authorId,authors.name"
UA = {"User-Agent": "research-script/0.1", "Content-Type": "application/json"}

def call(url, body=None):
    key = os.path.join(CACHE, hashlib.sha1((url + json.dumps(body or {}, sort_keys=True)).encode()).hexdigest() + ".json")
    if os.path.exists(key): return json.load(open(key))
    for attempt in range(12):
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, headers=UA)
            out = json.loads(urllib.request.urlopen(req, timeout=120).read())
            json.dump(out, open(key, "w")); time.sleep(1.5); return out
        except Exception as e:
            code = getattr(e, "code", 0)
            print("   retry", code or e, file=sys.stderr); time.sleep(min(60, 5 + 5 * attempt))
    return None

def main():
    papers = {}   # s2 paperId -> record
    def add(w, src):
        if not w or not w.get("title"): return
        p = papers.setdefault(w["paperId"], w); p.setdefault("src", set()).add(src)

    # (a) Observatory log
    ax = []
    for f in glob.glob(os.path.join(OBS, "*.json")):
        for it in json.load(open(f)):
            if it.get("ax") and it["d"] >= "2022": ax.append(it["ax"])
    ax = sorted(set(ax)); print("Observatory arXiv records 2022+:", len(ax))
    for i in range(0, len(ax), 400):
        d = call(f"{S2}/paper/batch?fields={FIELDS}", {"ids": ["ARXIV:" + a for a in ax[i:i + 400]]}) or []
        for w in d: add(w, "observatory")
        print("  batch", i, len(papers))

    # (b) topic searches
    totals = {}
    for slug, t in T.items():
        q = " | ".join('"' + p + '"' for p in t["phrases"])
        n = 0
        for sort in ("citationCount:desc", "publicationDate:desc"):
            url = f"{S2}/paper/search/bulk?" + urllib.parse.urlencode({"query": q, "year": "2022-", "fields": FIELDS, "sort": sort})
            d = call(url) or {}
            totals[slug] = d.get("total", 0)
            for w in d.get("data", []): add(w, "search:" + slug); n += 1
        print(f"  search {slug}: total {totals[slug]}, fetched {n}, corpus {len(papers)}")

    # topic assignment
    out = []
    for w in papers.values():
        tp = assign(w["title"], w.get("abstract"))
        if not tp or not w.get("abstract") or (w.get("year") or 0) < 2022: continue
        ext0 = w.get("externalIds") or {}
        if not ext0.get("ArXiv") and (w.get("citationCount") or 0) < 3: continue   # unreviewed, uncited, not on arXiv: skip
        ranked = sorted(tp, key=lambda k: -tp[k])
        ext = w.get("externalIds") or {}
        out.append(dict(id=w["paperId"], t=w["title"], ab=w.get("abstract") or "", y=w.get("year"), d=w.get("publicationDate"),
                        ax=ext.get("ArXiv"), doi=ext.get("DOI"), c=w.get("citationCount") or 0, v=w.get("venue") or "",
                        f=sorted({x["category"] for x in (w.get("s2FieldsOfStudy") or [])}),
                        au=[[a.get("authorId"), a.get("name")] for a in w.get("authors") or []],
                        tp=ranked[:3], tps={k: tp[k] for k in ranked[:3]}, src=sorted(w["src"])))
    json.dump(dict(papers=out, search_totals=totals), open(os.path.join(DATA, "corpus.json"), "w"))
    import collections
    c = collections.Counter(p["tp"][0] for p in out)
    print("corpus", len(out), "with arXiv id", sum(1 for p in out if p["ax"]), "no abstract", sum(1 for p in out if not p["ab"]))
    for k, n in c.most_common(): print(f"  {n:5d} {k}")

if __name__ == "__main__":
    main()
