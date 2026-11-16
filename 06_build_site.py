"""Step 6: build the site from site/template.html + site/data.json (+ site/shortlist.json, optional).

  site/index.html     standalone page (open in a browser, or host as a static site)
  site/artifact.html  the same page without the outer HTML skeleton, for publishing as a claude.ai artifact
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); SITE = os.path.join(HERE, "site")
safe = lambda s: s.replace("</", "<\\/")
tpl = open(os.path.join(SITE, "template.html")).read()
data = safe(open(os.path.join(SITE, "data.json")).read())
sl_fn = os.path.join(SITE, "shortlist.json")
sl = safe(json.dumps(json.load(open(sl_fn)), separators=(",", ":"))) if os.path.exists(sl_fn) else "{}"
page = tpl.replace("/*DATA*/", data).replace("/*SHORTLIST*/", sl)
open(os.path.join(SITE, "artifact.html"), "w").write(page)
head_end = page.index("</style>") + len("</style>")
open(os.path.join(SITE, "index.html"), "w").write(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    + page[:head_end].replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "") + "\n</head>\n<body>\n" + page[head_end:] + "\n</body>\n</html>\n")
print("built", os.path.getsize(os.path.join(SITE, "index.html")) // 1024, "kB")
