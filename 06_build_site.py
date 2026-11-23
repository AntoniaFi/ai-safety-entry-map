"""Step 6: build the site from site/template.html + site/data.json + site/projects.json (Starter Projects tab).

  docs/index.html     standalone page (open in a browser; GitHub Pages serves it from docs/)
  site/artifact.html  the same page without the outer HTML skeleton, for publishing as a claude.ai artifact
  docs/llms.txt, docs/data/*.json   for AI agents and scripts: a plain-text guide and the data with readable field names
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); SITE = os.path.join(HERE, "site"); DOCS = os.path.join(HERE, "docs")
safe = lambda s: s.replace("</", "<\\/")
tpl = open(os.path.join(SITE, "template.html")).read()
data = safe(open(os.path.join(SITE, "data.json")).read())
# Starter Projects: every cited paper must be in data.json, every quote word for word in that paper's open-question sentences
pj = json.load(open(os.path.join(SITE, "projects.json")))
D = json.loads(data.replace("<\\/", "</")); AX = {p["ax"] for p in D["papers"]}; TS = {t["slug"] for t in D["topics"]}; OQ = {}
for L in D["openq"].values():
    for ax, q in L: OQ.setdefault(ax, []).append(q)
bad = []
for p in pj["projects"]:
    if p["area"] not in TS: bad.append(f'{p["id"]}: unknown area {p["area"]}')
    for x in p["start"] + p["gap"]:
        if x["ax"] not in AX: bad.append(f'{p["id"]}: paper {x["ax"]} not in data.json')
    for g in p["gap"]:
        if not any(g["q"] in q for q in OQ.get(g["ax"], [])): bad.append(f'{p["id"]}: quote not found in {g["ax"]}: {g["q"][:60]}')
if bad: raise SystemExit("projects.json:\n  " + "\n  ".join(bad))
pj = safe(json.dumps({"projects": pj["projects"]}, ensure_ascii=False, separators=(",", ":")))
page = tpl.replace("/*DATA*/", data).replace("/*PROJECTS*/", pj)
open(os.path.join(SITE, "artifact.html"), "w").write(page)
head_end = page.index("</style>") + len("</style>")

# ---------- for agents: readable data files and llms.txt ----------
LV = dict(coding=["None", "Scripts", "Software", "Large systems"],
          ml_models=["None", "Use a model as given", "Run and fine-tune open models", "Work inside the model", "Build training methods"],
          maths=["No formal maths", "Applied statistics", "Linear algebra and optimisation", "Theorems and proofs"],
          compute=["Chat subscription", "API credits", "One consumer GPU", "Rented data-centre GPUs", "Cluster"],
          studies_with_people=["None", "Surveys and experiments"])
k5 = lambda k: max(0, k - 1)  # the pipeline writes six compute levels; the site merges "None" into "Chat subscription"
lvl = lambda dim, i: {"level": i, "label": LV[dim][i]}
TL = {t["slug"]: t["label"] for t in D["topics"]}
papers = [dict(arxiv=p["ax"], url="https://arxiv.org/abs/" + p["ax"], title=p["t"], date=p["d"] or str(p["y"]), year=p["y"],
               authors=[dict(name=a[0], openalex=("https://openalex.org/" + a[1]) if a[1] else None) for a in p.get("au") or []],
               citations=p["c"], area=p["tp"], area_label=TL.get(p["tp"]), other_areas=p.get("tp2") or [],
               needs=dict(coding=lvl("coding", p["cd"]), ml_models=lvl("ml_models", p["e"]), maths=lvl("maths", p["m"]),
                          compute=lvl("compute", k5(p["k"])), studies_with_people=lvl("studies_with_people", p["h"])),
               code=p.get("code"), open_model_billion_params=dict(smallest=p.get("lo"), largest=p.get("hi")),
               uses_closed_models=bool(p.get("cl")), fine_tunes=bool(p.get("ft")), works_inside_model=bool(p.get("wb")),
               fellowship_programmes=p.get("pr") or [], big_lab_author=bool(p.get("lab")), gpus=p.get("gpu") or [],
               study_design=p.get("dz") or [], survey_or_review=bool(p.get("sv")), level_evidence=p.get("why") or [])
          for p in D["papers"]]
def shares(L, names): return {n: L[i] for i, n in enumerate(names)} if L else None
areas = []
for t in D["topics"]:
    comp = t.get("comp"); comp = [comp[0] + comp[1]] + comp[2:] if comp and len(comp) == 6 else comp
    areas.append(dict(slug=t["slug"], label=t["label"], group=t["group"], papers=t["n"], papers_by_year=t["years"], read_in_full=t["n_ft"],
                      median_citations=t.get("cites_median"),
                      level_shares=dict(coding=shares(t.get("cod"), LV["coding"]), ml_models=shares(t.get("eng"), LV["ml_models"]),
                                        maths=shares(t.get("math"), LV["maths"]), compute=shares(comp, LV["compute"])),
                      share=dict(studies_with_people=t.get("human"), fine_tuning=t.get("finetune"), inside_model=t.get("whitebox"),
                                 shares_code=t.get("code"), statistics=t.get("stats"), fellowship_programme=t.get("program"),
                                 big_lab_author=t.get("frontier"), closed_models_only=t.get("closed_only")),
                      study_design=t.get("design"), people=t.get("people")))
projects = json.loads(pj.replace("<\\/", "</"))["projects"]
for p in projects:
    n = p["needs"]; p["needs_labelled"] = {d: lvl(d, n[i]) for i, d in enumerate(LV)}
os.makedirs(os.path.join(DOCS, "data"), exist_ok=True)
def dump(name, obj):
    json.dump(obj, open(os.path.join(DOCS, "data", name), "w"), ensure_ascii=False, separators=(",", ":"))
dump("papers.json", dict(built=D["meta"]["built"], levels=LV, papers=papers))
dump("areas.json", dict(built=D["meta"]["built"], levels=LV, areas=areas))
dump("projects.json", dict(built=D["meta"]["built"], levels=LV, projects=projects))
dump("open-questions.json", dict(built=D["meta"]["built"], note="Sentences copied word for word from the papers, in which the authors name a limitation or something left for future work.",
                                 areas={k: [dict(arxiv=ax, sentence=q) for ax, q in L] for k, L in D["openq"].items()}))
m = D["meta"]
open(os.path.join(DOCS, "llms.txt"), "w").write(f"""# AI Safety Entry Map

> Which AI-safety research areas can a newcomer enter with the skills and hardware they have now? A map built from {m['papers']:,} AI-safety papers in {len(D['topics'])} research areas, {m['fulltexts']:,} of them read in full and labelled for the coding, ML-model, maths and compute level they need and whether they involve a study with people. Made by Antonia Fichtbauer; a spin-off data analytics project of the AI Safety Observatory (https://aisafetyobservatory.com). Data built {m['built']}.

The page is one static HTML file. Everything below is also available as JSON, so you do not need to run the page.

## Data (JSON, readable field names)

- [Papers](data/papers.json): every paper read in full, with arXiv link, authors (OpenAlex ids), citations, research area, and the level it needs on each skill (`needs`), plus the evidence the level rests on (`level_evidence`).
- [Research areas](data/areas.json): per area, paper counts by year, the share of papers at each skill level (`level_shares`), method shares, study-design shares and author statistics (`people`: `first_new` = share of first authors in their first or second year of publishing; `noncs` = share of authors with earlier papers outside computer science).
- [Starter projects](data/projects.json): small research projects for newcomers (replications, extensions, surveys), each with the levels it needs, papers to start from, steps, quotes from papers showing why it is needed, and risks. `pool` says for which skill range it is shown.
- [Open questions](data/open-questions.json): sentences in which authors name a limitation or future work, by area.

## Skill levels

A paper is "within reach" when none of its levels is above the reader's level on that skill.

- Coding 0–3: {', '.join(f'{i} {x}' for i, x in enumerate(LV['coding']))}
- Working with ML models 0–4: {', '.join(f'{i} {x}' for i, x in enumerate(LV['ml_models']))}
- Maths 0–3: {', '.join(f'{i} {x}' for i, x in enumerate(LV['maths']))}
- Compute 0–4: {', '.join(f'{i} {x}' for i, x in enumerate(LV['compute']))}
- Studies with people 0–1: {', '.join(f'{i} {x}' for i, x in enumerate(LV['studies_with_people']))}

## Linking to the page

Tabs: `#home`, `#topics` (research areas), `#projects` (starter projects), `#papers`, `#questions`, `#method`, `#basket`.
Skill levels can be set in the link, for example `index.html#projects?c=2&e=2&m=1&k=2&h=0` (c coding, e ML models, m maths, k compute, h studies with people). On `#projects` this also applies the levels and shows the matching projects.

## Method and source

- [Method and code](https://github.com/AntoniaFi/ai-safety-entry-map): how papers are collected, read and labelled, the check against hand labels, and the limits.
- Claims on starter projects are GitHub issues with the label `claim`: https://github.com/AntoniaFi/ai-safety-entry-map/issues?q=label%3Aclaim
""")
jsonld = json.dumps({"@context": "https://schema.org", "@type": "Dataset", "name": "AI Safety Entry Map",
    "description": f"{m['papers']:,} AI-safety papers in {len(D['topics'])} research areas; {m['fulltexts']:,} of them read in full and labelled for the coding, ML-model, maths and compute level they need, with starter projects for newcomers.",
    "url": "https://antoniafi.github.io/ai-safety-entry-map/", "creator": {"@type": "Person", "name": "Antonia Fichtbauer"}, "dateModified": m["built"],
    "isPartOf": {"@type": "WebSite", "name": "AI Safety Observatory", "url": "https://aisafetyobservatory.com"},
    "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": "https://antoniafi.github.io/ai-safety-entry-map/data/" + f} for f in ("papers.json", "areas.json", "projects.json", "open-questions.json")]}, ensure_ascii=False)
agent_head = ('<link rel="alternate" type="text/plain" href="llms.txt" title="Guide for AI agents">\n'
              '<script type="application/ld+json">' + jsonld.replace("</", "<\\/") + '</script>\n')
noscript = ('<noscript><p>This page needs JavaScript. The same data is available without it: <a href="llms.txt">llms.txt</a> (guide), '
            '<a href="data/papers.json">papers</a>, <a href="data/areas.json">research areas</a>, <a href="data/projects.json">starter projects</a>, '
            '<a href="data/open-questions.json">open questions</a>.</p></noscript>\n')
os.makedirs(DOCS, exist_ok=True)
open(os.path.join(DOCS, "index.html"), "w").write(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<meta name="description" content="Which AI-safety research areas can you enter with the skills and hardware you have now? A map built from thousands of papers.">\n<meta name="author" content="Antonia Fichtbauer">\n'
    + agent_head + page[:head_end].replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "") + "\n</head>\n<body>\n" + noscript + page[head_end:] + "\n</body>\n</html>\n")
print("built", os.path.getsize(os.path.join(DOCS, "index.html")) // 1024, "kB")
