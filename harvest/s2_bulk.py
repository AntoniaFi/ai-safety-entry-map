"""Harvest Semantic Scholar through its bulk search (no login needed; a free API key in ~/.config/s2_key makes it faster and steadier).

For every area and field, all papers from 2018 on in Computer Science (or any field for the human-AI and risk lists) that
contain one of the strong phrases, 1,000 per request, following the continuation token to the end (at most MAX_PAGES).
Resumable. Usage: python3 s2_bulk.py
"""
import json, os, sys, time, urllib.parse, urllib.request
from store import connect, upsert, get_progress, set_progress
from queries import all_strong

S2 = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
FIELDS = "title,abstract,year,publicationDate,externalIds,citationCount,venue,publicationTypes,s2FieldsOfStudy,authors.name"
MAX_PAGES = 25
KEYF = os.path.expanduser("~/.config/s2_key")
HEAD = {"User-Agent": "research-script/0.1"}
if os.path.exists(KEYF): HEAD["x-api-key"] = open(KEYF).read().strip()

def get(params):
    url = S2 + "?" + urllib.parse.urlencode(params)
    for attempt in range(14):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=HEAD), timeout=120).read())
        except Exception as e:
            time.sleep(min(90, 6 + 6 * attempt))
    return None

def record(w):
    ext = w.get("externalIds") or {}; types = w.get("publicationTypes") or []
    venue = w.get("venue") or ("arXiv" if ext.get("ArXiv") and not ext.get("DOI") else None)
    return dict(arxiv=ext.get("ArXiv"), doi=ext.get("DOI"), s2=w["paperId"], title=w.get("title"), abstract=w.get("abstract"), date=w.get("publicationDate"),
                year=w.get("year"), venue=venue, kind="preprint" if (venue or "").lower().startswith("arxiv") else "paper", cites=w.get("citationCount"),
                authors=[a["name"] for a in (w.get("authors") or [])][:40], topics=None)

def main():
    c = connect(); fields, areas = all_strong()
    anyfield = {"human-ai", "general-risk", "human-oversight", "anthropomorphism-companions", "public-perception", "persuasion-manipulation", "safety-cases"}
    for name, phrases in list(areas.items()) + list(fields.items()):
        job = f"s2:{name}"; st = get_progress(c, job)
        if st.get("done"): continue
        q = " | ".join('"' + p + '"' for p in sorted({p.lower() for p in phrases}))
        params = {"query": q, "year": "2018-", "fields": FIELDS}
        if name not in anyfield: params["fieldsOfStudy"] = "Computer Science"
        token = st.get("token"); n = st.get("n", 0); pages = st.get("pages", 0); new = 0
        while pages < MAX_PAGES:
            d = get({**params, **({"token": token} if token else {})})
            if d is None: print(job, "no answer; will resume next run", flush=True); break
            for w in d.get("data") or []:
                if w.get("title"): new += upsert(c, record(w), "s2")[1]
            n += len(d.get("data") or []); pages += 1; token = d.get("token")
            set_progress(c, job, {"token": token, "n": n, "pages": pages, "total": d.get("total")})
            if not token: break
            time.sleep(1.2 if "x-api-key" in HEAD else 3.5)
        else:
            print(f"{job}: stopped at {MAX_PAGES} pages ({n} of {st.get('total')}) - query too broad", flush=True)
        if d is not None:
            set_progress(c, job, {"done": True, "n": n, "pages": pages, "total": d.get("total"), "capped": bool(token)})
            print(f"{job}: {n} of {d.get('total')} papers, {new} new", flush=True)
    print("Semantic Scholar harvest complete", flush=True)

if __name__ == "__main__":
    main()
