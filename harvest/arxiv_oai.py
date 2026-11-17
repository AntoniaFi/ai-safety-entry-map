"""Harvest arXiv metadata through OAI-PMH (free, no login): every paper in the AI-related categories, first submitted 2018 or later.

Walks the `cs` and `stat` sets month by month (by last-modified date) and keeps records that carry one of AI_CATS.
Resumable: finished months are remembered in the progress table. Re-run any time to pick up new months.
Usage: python3 arxiv_oai.py [first month, default 2018-01]
"""
import datetime, html, re, sys, time, urllib.parse, urllib.request
from store import connect, upsert, get_progress, set_progress

BASE = "https://oaipmh.arxiv.org/oai"
AI_CATS = {"cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.CR", "cs.CY", "cs.HC", "cs.MA", "cs.RO", "cs.SE", "cs.NE", "cs.IR", "cs.GT", "cs.LO", "cs.SI", "stat.ML", "econ.GN", "q-bio.QM"}
MIN_DATE = "2018-01-01"
UA = {"User-Agent": "research-script/0.1"}
MONTHS = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}

def fetch(url):
    for attempt in range(10):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180).read().decode("utf8", "ignore")
        except Exception as e:
            wait = 30 * (attempt + 1) if getattr(e, "code", 0) in (429, 503) else 10
            print("   retry", getattr(e, "code", e), "wait", wait, flush=True); time.sleep(wait)
    raise SystemExit("arXiv OAI not reachable")

def field(rec, tag):
    m = re.search(rf"<{tag}>(.*?)</{tag}>", rec, re.S)
    return re.sub(r"\s+", " ", html.unescape(m.group(1))).strip() if m else None

def parse(rec):
    cats = (field(rec, "categories") or "").split()
    if not AI_CATS & set(cats): return None
    d = re.search(r"<version version=\"v1\">\s*<date>\w+, (\d+) (\w+) (\d{4})", rec)
    if not d: return None
    date = f"{d.group(3)}-{MONTHS[d.group(2)]:02d}-{int(d.group(1)):02d}"
    if date < MIN_DATE: return None
    au = field(rec, "authors") or ""
    authors = [a.strip() for a in re.split(r",| and ", re.sub(r"\([^)]*\)", "", au)) if a.strip()][:40]
    jr = field(rec, "journal-ref")
    return dict(arxiv=field(rec, "id"), doi=field(rec, "doi"), title=field(rec, "title"), abstract=field(rec, "abstract"), date=date, year=int(date[:4]),
                venue=jr or "arXiv", kind="paper" if jr else "preprint", authors=authors, cats=" ".join(cats))

def month_iter(start):
    y, m = map(int, start.split("-")); today = datetime.date.today()
    while (y, m) <= (today.year, today.month):
        last = (datetime.date(y + (m == 12), m % 12 + 1, 1) - datetime.timedelta(days=1))
        yield f"{y}-{m:02d}", f"{y}-{m:02d}-01", min(last, today).isoformat()
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)

def main():
    c = connect(); done = get_progress(c, "arxiv_oai").get("done", [])
    start = sys.argv[1] if len(sys.argv) > 1 else "2018-01"
    this_month = datetime.date.today().strftime("%Y-%m")
    for st in ("cs", "stat"):
        for label, d1, d2 in month_iter(start):
            key = f"{st}:{label}"
            if key in done and label != this_month: continue
            url = f"{BASE}?verb=ListRecords&metadataPrefix=arXivRaw&set={st}&from={d1}&until={d2}"; seen = kept = new = 0
            while url:
                x = fetch(url)
                for rec in re.findall(r"<record>.*?</record>", x, re.S):
                    seen += 1; r = parse(rec)
                    if r:
                        kept += 1; new += upsert(c, r, "arxiv")[1]
                c.commit()
                tok = re.search(r"<resumptionToken[^>]*>([^<]+)</resumptionToken>", x)
                url = f"{BASE}?verb=ListRecords&resumptionToken={tok.group(1)}" if tok else None
                time.sleep(3)
            if key not in done: done.append(key)
            set_progress(c, "arxiv_oai", {"done": done})
            print(f"{key}: {seen} records, {kept} AI-category from 2018 on, {new} new", flush=True)
    print("arXiv harvest complete; works in store:", c.execute("SELECT count(*) FROM works").fetchone()[0], flush=True)

if __name__ == "__main__":
    main()
