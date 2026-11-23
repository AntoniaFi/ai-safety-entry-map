"""Step 6: build the site from site/template.html + site/data.json + site/projects.json (Starter Projects tab).

  docs/index.html     standalone page (open in a browser; GitHub Pages serves it from docs/)
  site/artifact.html  the same page without the outer HTML skeleton, for publishing as a claude.ai artifact
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
os.makedirs(DOCS, exist_ok=True)
open(os.path.join(DOCS, "index.html"), "w").write(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<meta name="description" content="Which AI-safety research areas can you enter with the skills and hardware you have now? A map built from thousands of papers.">\n<meta name="author" content="Antonia Fichtbauer">\n'
    + page[:head_end].replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "") + "\n</head>\n<body>\n" + page[head_end:] + "\n</body>\n</html>\n")
print("built", os.path.getsize(os.path.join(DOCS, "index.html")) // 1024, "kB")
