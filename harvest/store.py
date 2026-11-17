"""The universe store: one SQLite file (data/universe.sqlite) holding every candidate record from every source.

One row per work. A work is recognised across sources by its arXiv id, else its DOI, else its normalised title (same year +-1).
Fields are filled from whichever source has them; `src` lists every source that reported the work.
"""
import json, os, re, sqlite3, time, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "..", "data")
DB = os.path.join(DATA, "universe.sqlite")

SCHEMA = """
CREATE TABLE IF NOT EXISTS works(
  wid INTEGER PRIMARY KEY, arxiv TEXT, doi TEXT, openalex TEXT, s2 TEXT, lw TEXT,
  title TEXT, tnorm TEXT, abstract TEXT, date TEXT, year INTEGER, venue TEXT, kind TEXT,
  authors TEXT, cats TEXT, topics TEXT, cites INTEGER, lang TEXT, src TEXT, added TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS ix_arxiv ON works(arxiv) WHERE arxiv IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_doi ON works(doi);
CREATE INDEX IF NOT EXISTS ix_tnorm ON works(tnorm);
CREATE INDEX IF NOT EXISTS ix_openalex ON works(openalex);
CREATE INDEX IF NOT EXISTS ix_s2 ON works(s2);
CREATE TABLE IF NOT EXISTS progress(job TEXT PRIMARY KEY, state TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS labels(wid INTEGER PRIMARY KEY, score REAL, safety INTEGER, fields TEXT, areas TEXT, lf TEXT, version TEXT);
CREATE TABLE IF NOT EXISTS gold(wid INTEGER PRIMARY KEY, safety INTEGER, note TEXT, who TEXT, at TEXT, batch TEXT);
"""

def connect():
    os.makedirs(DATA, exist_ok=True)
    c = sqlite3.connect(DB, timeout=120); c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA synchronous=NORMAL")
    c.executescript(SCHEMA); return c

def tnorm(t):
    t = unicodedata.normalize("NFKC", t or "").lower()
    t = re.sub(r"[^a-z0-9]+", " ", t).strip()
    return t if len(t) >= 20 else None        # very short titles are not safe to match on

def clean_doi(d):
    if not d: return None
    d = d.lower().strip().replace("https://doi.org/", "").replace("http://dx.doi.org/", "")
    m = re.match(r"10\.48550/arxiv\.(.+)", d)
    return None if m else d                   # an arXiv DOI is not a separate identity; the arXiv id carries it

def arxiv_from_doi(d):
    m = re.match(r"(?:https://doi.org/)?10\.48550/arxiv\.(\d{4}\.\d{4,5})", (d or "").lower())
    return m.group(1) if m else None

FILL = ("doi", "openalex", "s2", "lw", "title", "abstract", "date", "year", "venue", "kind", "authors", "cats", "topics", "lang")

def upsert(c, r, src):
    """r: dict with any of the works columns. Returns (wid, is_new)."""
    r = dict(r); r["doi"] = clean_doi(r.get("doi")); r["tnorm"] = tnorm(r.get("title"))
    for k in ("authors", "topics"):
        if isinstance(r.get(k), (list, dict)): r[k] = json.dumps(r[k], ensure_ascii=False)
    row = None
    if r.get("arxiv"): row = c.execute("SELECT * FROM works WHERE arxiv=?", (r["arxiv"],)).fetchone()
    for key in ("openalex", "s2", "doi"):
        if row is None and r.get(key): row = c.execute(f"SELECT * FROM works WHERE {key}=?", (r[key],)).fetchone()
    if row is None and r["tnorm"]:
        y = r.get("year")
        for cand in c.execute("SELECT * FROM works WHERE tnorm=?", (r["tnorm"],)).fetchall():
            cy = cand[10]
            if y is None or cy is None or abs(cy - y) <= 1:
                # never join two records that carry different arXiv ids
                if r.get("arxiv") and cand[1] and cand[1] != r["arxiv"]: continue
                row = cand; break
    if row is None:
        c.execute("INSERT INTO works(arxiv,doi,openalex,s2,lw,title,tnorm,abstract,date,year,venue,kind,authors,cats,topics,cites,lang,src,added) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (r.get("arxiv"), r["doi"], r.get("openalex"), r.get("s2"), r.get("lw"), r.get("title"), r["tnorm"], r.get("abstract"), r.get("date"), r.get("year"),
                   r.get("venue"), r.get("kind"), r.get("authors"), r.get("cats"), r.get("topics"), r.get("cites"), r.get("lang"), src, time.strftime("%Y-%m-%d")))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0], True
    cols = [d[1] for d in c.execute("PRAGMA table_info(works)")]; cur = dict(zip(cols, row)); sets = {}
    if r.get("arxiv") and not cur["arxiv"]: sets["arxiv"] = r["arxiv"]
    for k in FILL:
        v = r.get(k)
        if v in (None, ""): continue
        if cur[k] in (None, ""): sets[k] = v
        elif k == "abstract" and len(v) > len(cur[k]) * 1.3: sets[k] = v           # keep the fuller abstract
        elif k == "venue" and re.search(r"arxiv", cur[k] or "", re.I) and not re.search(r"arxiv", v, re.I): sets[k] = v; sets["kind"] = r.get("kind") or cur["kind"]
    if r.get("cites") is not None and (cur["cites"] is None or r["cites"] > cur["cites"]): sets["cites"] = r["cites"]
    srcs = set((cur["src"] or "").split(",")) - {""}
    if src not in srcs: sets["src"] = ",".join(sorted(srcs | {src}))
    if sets: c.execute("UPDATE works SET " + ",".join(f"{k}=?" for k in sets) + " WHERE wid=?", (*sets.values(), cur["wid"]))
    return cur["wid"], False

def get_progress(c, job):
    r = c.execute("SELECT state FROM progress WHERE job=?", (job,)).fetchone()
    return json.loads(r[0]) if r else {}

def set_progress(c, job, state):
    c.execute("INSERT INTO progress(job,state,updated) VALUES(?,?,?) ON CONFLICT(job) DO UPDATE SET state=excluded.state, updated=excluded.updated",
              (job, json.dumps(state), time.strftime("%Y-%m-%d %H:%M")))
    c.commit()
