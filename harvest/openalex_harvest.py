"""Harvest OpenAlex (needs ~/.config/openalex_key; 10,000 credits a day, reset 01:00 CET).

  topics   every work from 2018 on whose primary topic is one of queries.OPENALEX_TOPICS      (1 credit per 200 works)
  search   every work from 2018 on whose title or abstract contains a strong phrase            (10 credits per 200 works)

Stops when the day's remaining credits fall below RESERVE (kept for the Observatory's morning sweep); re-run the next day and
it continues where it stopped. Usage: python3 openalex_harvest.py topics|search|all [reserve, default 4500]
"""
import json, os, sys, time, urllib.parse, urllib.request
from store import connect, upsert, get_progress, set_progress, arxiv_from_doi
from queries import FIELDS, OPENALEX_TOPICS, all_strong
AI_CONTEXT = ["machine learning", "deep learning", "neural network", "neural networks", "language model", "language models", "LLM", "LLMs", "reinforcement learning",
              "artificial intelligence", "AI system", "AI systems", "AI models", "generative AI", "chatbot", "AI agents", "foundation models"]
CAP = 20000        # most relevant works kept per search query; a query with more hits is too broad and is logged

KEY = open(os.path.expanduser("~/.config/openalex_key")).read().strip()
SELECT = "id,doi,ids,title,publication_date,publication_year,type,language,primary_location,primary_topic,cited_by_count,abstract_inverted_index"
RESERVE = int(sys.argv[2]) if len(sys.argv) > 2 else 4500
remaining = [10000]

def get(**p):
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode({**p, "api_key": KEY})
    for attempt in range(8):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "research-script/0.1"}), timeout=120)
            remaining[0] = int(float(r.headers.get("X-RateLimit-Remaining") or remaining[0])); return json.loads(r.read())
        except Exception as e:
            code = getattr(e, "code", 0)
            if code == 400: print("   bad request:", getattr(e, "read", lambda: b"")()[:200], flush=True); return None
            if code == 429: remaining[0] = 0; return None
            time.sleep(3 + 3 * attempt)
    return None

def abstract(inv):
    if not inv: return None
    pos = sorted((i, w) for w, idx in inv.items() for i in idx)
    return " ".join(w for _, w in pos)[:6000]

def record(w):
    loc = w.get("primary_location") or {}; srcname = ((loc.get("source") or {}).get("display_name")) or ""
    ax = arxiv_from_doi(w.get("doi")) or None
    lp = (loc.get("landing_page_url") or "")
    if not ax and "arxiv.org/abs/" in lp: ax = lp.split("arxiv.org/abs/")[-1].split("v")[0]
    t = w.get("primary_topic") or {}
    kind = "preprint" if w.get("type") == "preprint" or "arxiv" in srcname.lower() else "paper"
    return dict(arxiv=ax, doi=w.get("doi"), openalex=w["id"].split("/")[-1], title=w.get("title"), abstract=abstract(w.get("abstract_inverted_index")),
                date=w.get("publication_date"), year=w.get("publication_year"), venue=srcname or None, kind=kind, cites=w.get("cited_by_count"), lang=w.get("language"),
                topics={"id": (t.get("id") or "").split("/")[-1], "name": t.get("display_name"), "field": (t.get("field") or {}).get("display_name")} if t else None)

def run(c, job, flt, cost, cap=None):
    st = get_progress(c, job)
    if st.get("done"): print(job, "already complete"); return True
    cursor = st.get("cursor", "*"); n = st.get("n", 0); new = 0
    while cursor:
        if remaining[0] - cost < RESERVE: print(f"{job}: paused at {n} works, {remaining[0]} credits left (reserve {RESERVE})", flush=True); return False
        d = get(filter=flt, select=SELECT, per_page=200, cursor=cursor)
        if d is None: print(f"{job}: stopped (no answer or daily limit) at {n}", flush=True); return False
        for w in d["results"]:
            if w.get("title"): new += upsert(c, record(w), "openalex")[1]
        n += len(d["results"]); cursor = d["meta"].get("next_cursor") if d["results"] else None
        set_progress(c, job, {"cursor": cursor, "n": n, "total": d["meta"]["count"]})
        if cap and n >= cap and cursor:
            set_progress(c, job, {"done": True, "n": n, "total": d["meta"]["count"], "capped": True})
            print(f"{job}: capped at {n} of {d['meta']['count']} (query too broad)", flush=True); return True
        if n % 5000 < 200: print(f"   {job}: {n} of {d['meta']['count']}, {new} new this run, credits left {remaining[0]}", flush=True)
        time.sleep(0.25)
    set_progress(c, job, {"done": True, "n": n}); print(f"{job}: complete, {n} works, {new} new", flush=True); return True

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"; c = connect()
    base = "publication_year:>2017,type:article|preprint|book-chapter|review|report|dissertation"
    if mode in ("topics", "all"):
        for tid in OPENALEX_TOPICS:
            if not run(c, f"openalex:topic:{tid}", f"{base},primary_topic.id:{tid}", 1): return
    if mode in ("search", "all"):
        fields, areas = all_strong()
        # skip what the topic harvest already holds and works whose only home is arXiv (the arXiv harvest has those in full)
        skip = "".join(f",primary_topic.id:!{t}" for t in OPENALEX_TOPICS) + ",primary_location.source.id:!S4306400194"
        ctx = " OR ".join('"' + w + '"' for w in AI_CONTEXT)
        order = list(areas.items()) + [(k, fields[k]) for k in ("alignment", "general-risk", "monitoring-control", "assurance", "robustness", "human-ai", "multi-agent", "bias-fairness", "explainability")]
        for name, phrases in order:
            ph = sorted({p.lower() for p in phrases if len(p) > 5})
            for i in range(0, len(ph), 12):                                   # 12 phrases per query keeps the URL short
                q = "(" + " OR ".join('"' + p + '"' for p in ph[i:i + 12]) + ") AND (" + ctx + ")"
                if not run(c, f"openalex:search2:{name}:{i // 12}", f"{base}{skip},title_and_abstract.search:{q}", 10, cap=CAP): return
    print("OpenAlex harvest complete for mode", mode, "- credits left", remaining[0], flush=True)

if __name__ == "__main__":
    main()
