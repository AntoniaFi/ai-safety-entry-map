"""Step 3: the people table (OpenAlex).

For every core corpus paper from 2023 on, find the paper in OpenAlex (by arXiv DOI, else journal DOI, else title for the
focus topics) and take its authors with OpenAlex author ids and institutions. For a sample of authors (all first authors
and everyone in the focus topics first, then at random up to MAX_PEOPLE) fetch their 25 earliest works: this gives the year
of first publication and the fields they published in BEFORE their first paper in this corpus (their background).

Output: data/people.json, data/people.csv (names; stays local), data/authorships.json
Uses the OpenAlex key in ~/.config/openalex_key; one credit per request, every request cached in data/cache_oa/.

Limits (state them wherever the numbers are shown):
- "Years since first publication" stands in for "years since degree". A first paper usually appears during a Master's or
  early PhD, so it runs a few years ahead of years-since-PhD.
- OpenAlex sometimes merges two people with the same name. Profiles with more than 400 works, or a first paper more than
  45 years before, are excluded.
- A person with no earlier publications has an unknown background (student, or a career changer from industry).
- About a third of arXiv preprints are not in OpenAlex; their authors are missing.
(An earlier version used Semantic Scholar author profiles. They split many researchers into an old and a new profile,
which made established researchers look like newcomers, so it was replaced.)
"""
import collections, csv, hashlib, json, os, random, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "data")
CACHE = os.path.join(DATA, "cache_oa"); os.makedirs(CACHE, exist_ok=True)
KEY = open(os.path.expanduser("~/.config/openalex_key")).read().strip()
MAX_PEOPLE = 6000; MAX_TITLE_SEARCH = 60
RESERVE = 4600          # OpenAlex credits left untouched for the Observatory's morning sweep
remaining = [10000]
FOCUS = {"emergent-misalignment", "personas", "model-organisms", "evaluation-awareness", "sandbagging", "scheming-deception",
         "sycophancy", "cot-monitoring", "introspection-selfknowledge", "values-preferences", "personality-psychometrics"}
BG = {"Computer Science": "Computer science / ML", "Decision Sciences": "Mathematics", "Mathematics": "Mathematics",
      "Physics and Astronomy": "Physics", "Engineering": "Engineering", "Materials Science": "Engineering",
      "Chemical Engineering": "Engineering", "Energy": "Engineering", "Psychology": "Psychology & cognitive science",
      "Neuroscience": "Psychology & cognitive science", "Social Sciences": "Social sciences, economics & law",
      "Economics, Econometrics and Finance": "Social sciences, economics & law", "Business, Management and Accounting": "Social sciences, economics & law",
      "Arts and Humanities": "Philosophy & humanities"}
LIFE = "Natural & life sciences"   # every other OpenAlex field (medicine, biology, chemistry, earth and environmental sciences ...)
calls = [0]

def get(path, **p):
    raw = path + "?" + urllib.parse.urlencode(sorted(p.items()))
    key = os.path.join(CACHE, hashlib.sha1(raw.encode()).hexdigest() + ".json")
    if os.path.exists(key): return json.load(open(key))
    for attempt in range(6):
        try:
            if remaining[0] < RESERVE: return None
            r = urllib.request.urlopen(urllib.request.Request("https://api.openalex.org/" + raw + "&api_key=" + KEY, headers={"User-Agent": "research-script/0.1"}), timeout=60)
            remaining[0] = int(float(r.headers.get("X-RateLimit-Remaining") or remaining[0]))
            out = json.loads(r.read()); json.dump(out, open(key, "w")); calls[0] += 1; return out
        except Exception as e:
            code = getattr(e, "code", 0)
            if code in (400, 404): return None
            time.sleep(1 + 2 * attempt)
    return None

norm = lambda t: re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()

def main():
    P = [p for p in json.load(open(os.path.join(DATA, "corpus.json")))["papers"] if p["tps"][p["tp"][0]] >= 2 and (p["y"] or 0) >= 2023]
    SEL = "id,doi,title,publication_year,authorships"
    found = {}                       # corpus paper id -> OpenAlex work
    def take(works, by):
        for w in works or []:
            k = by(w)
            if k and k not in found and w.get("authorships"): found[k] = w
    # 0) the OpenAlex id the store already holds
    oid = {p["oa"]: p["id"] for p in P if p.get("oa")}; ids = sorted(oid)
    for i in range(0, len(ids), 50):
        d = get("works", filter="openalex:" + "|".join(ids[i:i + 50]), select=SEL, per_page=100)
        take((d or {}).get("results"), lambda w: oid.get(w["id"].split("/")[-1]))
    print("found by OpenAlex id", len(found), flush=True)
    # 1) arXiv DOI, 2) other DOI
    ax = {p["ax"].lower(): p["id"] for p in P if p["ax"]}; ids = sorted(ax)
    for i in range(0, len(ids), 50):
        d = get("works", filter="doi:" + "|".join("10.48550/arxiv." + a for a in ids[i:i + 50]), select=SEL, per_page=100)
        take((d or {}).get("results"), lambda w: ax.get((w.get("doi") or "").lower().split("arxiv.")[-1]))
    dois = {p["doi"].lower(): p["id"] for p in P if p["id"] not in found and p["doi"] and "arxiv" not in p["doi"].lower()}; ids = sorted(dois)
    for i in range(0, len(ids), 50):
        d = get("works", filter="doi:" + "|".join(ids[i:i + 50]), select=SEL, per_page=100)
        take((d or {}).get("results"), lambda w: dois.get((w.get("doi") or "").lower().replace("https://doi.org/", "")))
    print("papers", len(P), "found by DOI", len(found), flush=True)
    # 3) title search (10 credits each): the most cited missing papers of the focus topics
    miss = sorted([p for p in P if p["id"] not in found and p["tp"][0] in FOCUS], key=lambda p: -p["c"])[:MAX_TITLE_SEARCH]
    for p in miss:
        d = get("works", filter="title.search:" + re.sub(r"[^\w\s-]", " ", p["t"]), select=SEL, per_page=5)
        for w in (d or {}).get("results") or []:
            if norm(w.get("title")) == norm(p["t"]) and w.get("authorships"): found[p["id"]] = w; break
    print("found after title search", len(found), "requests so far", calls[0], flush=True)

    # authorships
    apps = collections.defaultdict(list); inst = {}
    PB = {p["id"]: p for p in P}
    A = []
    for pid, w in found.items():
        p = PB[pid]; n = len(w["authorships"])
        for i, a in enumerate(w["authorships"]):
            aid = (a["author"].get("id") or "").split("/")[-1]
            if not aid: continue
            pos = "first" if i == 0 else "last" if i == n - 1 and n > 2 else "middle"
            types = sorted({x.get("type") for x in a.get("institutions") or [] if x.get("type")})
            apps[aid].append((p["y"], p["tp"][0], pos, pid, types, (a.get("countries") or [None])[0], a["author"].get("display_name")))
    json.dump({pid: [[(a["author"].get("id") or "").split("/")[-1], sorted({x.get("type") for x in a.get("institutions") or [] if x.get("type")})] for a in w["authorships"]] for pid, w in found.items()},
              open(os.path.join(DATA, "authorships.json"), "w"))
    # sample of people
    random.seed(12); ids = sorted(apps)
    pri = [a for a in ids if any(pos == "first" or t in FOCUS for _, t, pos, *_ in apps[a])]
    rest = [a for a in ids if a not in set(pri)]; random.shuffle(rest); random.shuffle(pri)
    pick = (pri + rest)[:MAX_PEOPLE]
    print("authors", len(ids), "priority", len(pri), "fetching", len(pick), flush=True)
    def early(aid):
        return aid, get("works", filter=f"author.id:{aid}", sort="publication_date:asc", per_page=25, select="publication_year,primary_topic,type")
    rows = []
    with ThreadPoolExecutor(6) as ex:
        for aid, d in ex.map(early, pick):
            if not d or not d.get("results"): continue
            ap = apps[aid]; entry = min(a[0] for a in ap); total = d["meta"]["count"]
            W = [w for w in d["results"] if w.get("publication_year") and w.get("type") not in ("dataset", "paratext", "peer-review", "erratum", "editorial", "letter", "supplementary-materials", "other")]
            years = sorted(w["publication_year"] for w in W)
            if not years: continue
            while len(years) > 1 and years[1] - years[0] > 8: years = years[1:]
            first = min(years[0], entry)
            prior = [w for w in W if first <= w["publication_year"] < entry]
            fc = collections.Counter()
            for w in prior:
                f = ((w.get("primary_topic") or {}).get("field") or {}).get("display_name")
                if f: fc[BG.get(f, LIFE)] += 1
            n = sum(fc.values())
            if not prior: bg = "No earlier papers (unknown)"
            elif not n: bg = "Other / unclear"
            elif (n - fc["Computer science / ML"]) / n >= 0.5: bg = max((v, k) for k, v in fc.items() if k != "Computer science / ML")[1]
            else: bg = "Computer science / ML"
            thesis = next((w["publication_year"] for w in W if w.get("type") == "dissertation"), None)
            tcount = collections.Counter(a[1] for a in ap); types = collections.Counter(t for a in ap for t in a[4])
            rows.append(dict(id=aid, name=ap[0][6], first_pub=first, entry=entry, age_at_entry=entry - first, prior_papers=len(prior) if total <= 25 else max(len(prior), total - 25),
                             total_papers=total, background=bg, fields=dict(fc.most_common(4)), thesis_year=thesis,
                             inst_type=types.most_common(1)[0][0] if types else None, country=next((a[5] for a in ap if a[5]), None),
                             corpus_papers=len(ap), main_topic=tcount.most_common(1)[0][0], topics=dict(tcount),
                             positions=dict(collections.Counter(a[2] for a in ap)), apps=[[a[0], a[1], a[2], a[3]] for a in ap]))
    kept = [r for r in rows if r["age_at_entry"] <= 45 and r["total_papers"] <= 400]
    print("profiles", len(rows), "kept after plausibility filter", len(kept), "requests", calls[0], "credits left", remaining[0])
    json.dump(kept, open(os.path.join(DATA, "people.json"), "w"))
    with open(os.path.join(DATA, "people.csv"), "w", newline="") as f:
        cols = ["name", "main_topic", "corpus_papers", "entry", "first_pub", "age_at_entry", "thesis_year", "prior_papers", "total_papers", "background", "inst_type", "country", "positions", "fields"]
        w = csv.writer(f); w.writerow(cols)
        for r in sorted(kept, key=lambda r: (r["main_topic"], r["age_at_entry"])): w.writerow([json.dumps(r[c]) if isinstance(r[c], dict) else r[c] for c in cols])
    print(collections.Counter(r["background"] for r in kept).most_common())
    print("with a thesis record", sum(1 for r in kept if r["thesis_year"]))

if __name__ == "__main__":
    main()
