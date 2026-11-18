"""Step 6: build the site from site/template.html + site/data.json (+ site/shortlist.json, optional).

  docs/index.html     standalone page (open in a browser; GitHub Pages serves it from docs/)
  site/artifact.html  the same page without the outer HTML skeleton, for publishing as a claude.ai artifact
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); SITE = os.path.join(HERE, "site"); DOCS = os.path.join(HERE, "docs")
safe = lambda s: s.replace("</", "<\\/")
tpl = open(os.path.join(SITE, "template.html")).read()
data = safe(open(os.path.join(SITE, "data.json")).read())
sl_fn = os.path.join(SITE, "shortlist.json")
sl = safe(json.dumps(json.load(open(sl_fn)), separators=(",", ":"))) if os.path.exists(sl_fn) else "{}"
page = tpl.replace("/*DATA*/", data).replace("/*SHORTLIST*/", sl)
open(os.path.join(SITE, "artifact.html"), "w").write(page)
head_end = page.index("</style>") + len("</style>")
os.makedirs(DOCS, exist_ok=True)
open(os.path.join(DOCS, "index.html"), "w").write(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<meta name="description" content="Which AI-safety research areas can you enter with the skills and hardware you have now? A map built from thousands of papers.">\n<meta name="author" content="Antonia Fichtbauer">\n'
    + page[:head_end].replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "") + "\n</head>\n<body>\n" + page[head_end:] + "\n</body>\n</html>\n")
print("built", os.path.getsize(os.path.join(DOCS, "index.html")) // 1024, "kB")
