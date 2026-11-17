"""Decide which records in the store are AI-safety research, and of which kind. Run with the project's .venv Python.

Follows the Emerging Technology Observatory's recipe (https://eto.tech/dataset-docs/mac/) with open tools:
  1. labelling rules: phrase lists per field (queries.py) and per area (taxonomy.py) give each record a rough label:
     clearly in, clearly out, or undecided;
  2. a text classifier (logistic regression on word and word-pair counts) learns from the clear cases and scores every record;
  3. a record counts as AI safety if the rules say "clearly in", or its score is above the threshold AND it mentions AI;
  4. the threshold and the error rates come from hand labels (gold table; see gold.py).

Writes the labels table and data/universe_summary.json.   Usage: .venv/bin/python harvest/classify.py [threshold]
"""
import collections, json, multiprocessing, os, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, ".."))
from store import connect, DATA
from queries import FIELDS, AI_WORDS
from taxonomy import assign

VERSION = "v1"
def alt(words): return re.compile(r"\b(" + "|".join(re.escape(w).replace(r"\ ", r"[\s-]+").replace(r"\-", r"[\s-]?") for w in sorted(words, key=len, reverse=True)) + r")\b", re.I)
AI_RX = alt(AI_WORDS)
F_STRONG = {k: alt(v["strong"]) for k, v in FIELDS.items()}; F_WEAK = {k: alt(v["weak"]) for k, v in FIELDS.items()}
# safety of something else, with AI as the tool: ETO leaves these out, and so do we unless a strong phrase is present
DOMAIN = re.compile(r"\b(intrusion detection|malware|traffic safety|road safety|driving safety|food safety|drug safety|patient safety|fire safety|structural health|"
                    r"occupational safety|construction safety|mine safety|aviation safety|railway safety|nuclear safety|battery safety|pedestrian safety|"
                    r"differential privacy|federated learning|homomorphic encryption|side-channel|physical layer security)\b", re.I)

def rules(args):
    wid, title, abstract = args
    t = title or ""; a = abstract or ""; both = t + " . " + a
    ai = bool(AI_RX.search(both)); fields = {}; strong_total = 0; weak_total = 0; hits = []
    for k in FIELDS:
        st = F_STRONG[k].findall(t); sa = F_STRONG[k].findall(a); s = 3 * len(st) + len(sa)
        w = len(F_WEAK[k].findall(both)); weak_total += w; strong_total += s
        if s >= 1:
            fields[k] = s + min(w, 4) * 0.25; hits += [x.lower() if isinstance(x, str) else x[0].lower() for x in (st + sa)[:3]]
    areas = assign(t, a); top_area = max(areas.values()) if areas else 0
    domain = bool(DOMAIN.search(both))
    pos = ai and (top_area >= 2 or any(v >= 2 for v in fields.values()) or len(fields) >= 2)
    if domain and top_area < 2 and sum(1 for v in fields.values() if v >= 3) == 0: pos = False
    neg = (not areas) and strong_total == 0 and weak_total == 0
    weak = 1 if pos else 0 if neg else None
    return wid, weak, ai, fields, {k: v for k, v in areas.items() if v >= 2}, sorted(set(hits))[:6], domain

def main():
    from sklearn.feature_extraction.text import HashingVectorizer, TfidfTransformer
    from sklearn.linear_model import SGDClassifier
    import numpy as np, random
    c = connect(); t0 = time.time()
    rows = c.execute("SELECT wid, title, abstract FROM works WHERE year >= 2018 AND title IS NOT NULL").fetchall()
    print("records from 2018 on:", len(rows), flush=True)
    with multiprocessing.Pool(8) as pool: R = pool.map(rules, rows, chunksize=2000)
    print("rules done", round(time.time() - t0), "s", flush=True)
    text = {wid: ((t or "") + " . " + (a or "")) for wid, t, a in rows}
    has_abs = {wid: bool(a and len(a) > 200) for wid, t, a in rows}
    pos = [r[0] for r in R if r[1] == 1 and has_abs[r[0]]]; neg = [r[0] for r in R if r[1] == 0 and has_abs[r[0]] and r[2]]
    random.seed(3); neg_s = random.sample(neg, min(len(neg), 3 * len(pos)))
    print("clear cases with an abstract: in", len(pos), "out", len(neg), "(training on", len(pos), "+", len(neg_s), ")", flush=True)
    hv = HashingVectorizer(ngram_range=(1, 2), n_features=2 ** 20, alternate_sign=False, stop_words="english", lowercase=True, dtype=np.float32)
    Xtr = hv.transform([text[w] for w in pos + neg_s]); tf = TfidfTransformer(sublinear_tf=True).fit(Xtr)
    clf = SGDClassifier(loss="log_loss", alpha=2e-6, max_iter=25, tol=None, random_state=0, class_weight="balanced")
    clf.fit(tf.transform(Xtr), [1] * len(pos) + [0] * len(neg_s))
    ids = [r[0] for r in R]; scores = np.zeros(len(ids), dtype=np.float32)
    for i in range(0, len(ids), 50000):
        scores[i:i + 50000] = clf.predict_proba(tf.transform(hv.transform([text[w] for w in ids[i:i + 50000]])))[:, 1]
    print("scored", round(time.time() - t0), "s", flush=True)
    thr = float(sys.argv[1]) if len(sys.argv) > 1 else json.load(open(os.path.join(DATA, "threshold.json")))["threshold"] if os.path.exists(os.path.join(DATA, "threshold.json")) else 0.80
    c.execute("DELETE FROM labels")
    out = []
    for (wid, weak, ai, fields, areas, hits, domain), s in zip(R, scores):
        safety = 1 if (weak == 1 or (s >= thr and ai and has_abs[wid] and not (domain and not fields))) else 0
        out.append((wid, float(s), safety, json.dumps(fields) if fields else None, json.dumps(areas) if areas else None,
                    json.dumps({"rule": weak, "ai": ai, "hits": hits, "domain": domain, "abs": has_abs[wid]}), VERSION))
    c.executemany("INSERT INTO labels(wid,score,safety,fields,areas,lf,version) VALUES(?,?,?,?,?,?,?)", out); c.commit()
    summarise(c, thr)

def summarise(c, thr):
    S = dict(threshold=thr, built=time.strftime("%Y-%m-%d %H:%M"))
    S["store"] = dict(works=c.execute("SELECT count(*) FROM works").fetchone()[0],
                      from_2018=c.execute("SELECT count(*) FROM works WHERE year>=2018").fetchone()[0],
                      with_abstract=c.execute("SELECT count(*) FROM works WHERE year>=2018 AND length(abstract)>200").fetchone()[0])
    S["safety_total"] = c.execute("SELECT count(*) FROM labels WHERE safety=1").fetchone()[0]
    S["by_year"] = {str(y): n for y, n in c.execute("SELECT w.year, count(*) FROM works w JOIN labels l USING(wid) WHERE l.safety=1 GROUP BY w.year ORDER BY w.year")}
    S["by_year_rule_only"] = {str(y): n for y, n in c.execute("SELECT w.year, count(*) FROM works w JOIN labels l USING(wid) WHERE json_extract(l.lf,'$.rule')=1 GROUP BY w.year ORDER BY w.year")}
    S["by_year_narrow"] = {str(y): n for y, n in c.execute("SELECT w.year, count(*) FROM works w JOIN labels l USING(wid) WHERE l.areas IS NOT NULL GROUP BY w.year ORDER BY w.year")}
    fy = collections.defaultdict(collections.Counter); src = collections.Counter(); venues = collections.Counter(); kinds = collections.Counter()
    for year, fields, s, venue, arxiv, kind in c.execute("SELECT w.year, l.fields, w.src, w.venue, w.arxiv, w.kind FROM works w JOIN labels l USING(wid) WHERE l.safety=1"):
        for k in (json.loads(fields) if fields else {"(classifier only)": 1}): fy[k][str(year)] += 1
        src[s] += 1; kinds["on arXiv" if arxiv else "not on arXiv"] += 1
        if not arxiv and venue and not re.search(r"arxiv|ssrn|zenodo|research square|preprint|osf|techrxiv|hal ", venue, re.I): venues[venue] += 1
    S["by_field_year"] = {k: dict(v) for k, v in fy.items()}; S["by_source"] = dict(src.most_common()); S["on_arxiv"] = dict(kinds)
    S["top_venues_not_on_arxiv"] = venues.most_common(60)
    S["eto"] = {"2018-2023": 45000, "2019-2024": 55567}
    S["ours"] = {"2018-2023": sum(n for y, n in S["by_year"].items() if "2018" <= y <= "2023"), "2019-2024": sum(n for y, n in S["by_year"].items() if "2019" <= y <= "2024"),
                 "2018-2026": sum(n for y, n in S["by_year"].items() if "2018" <= y <= "2026")}
    S["progress"] = {j: json.loads(s) for j, s in c.execute("SELECT job, state FROM progress")}
    json.dump(S, open(os.path.join(DATA, "universe_summary.json"), "w"), indent=1)
    print(json.dumps({k: S[k] for k in ("store", "safety_total", "by_year", "by_year_narrow", "ours", "eto", "on_arxiv", "by_source")}, indent=1))
    print("fields:", {k: sum(v.values()) for k, v in S["by_field_year"].items()})

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "summary": summarise(connect(), json.load(open(os.path.join(DATA, "threshold.json")))["threshold"])
    else: main()
