# AI Safety Entry Map (niche finder)

Which AI-safety research areas can someone enter with the skills and hardware they have now?
Started 16 Nov 2026. Site source: `site/` (open `site/index.html` in a browser).

## Run
```
python3 01_corpus.py      # papers: Observatory sources log + Semantic Scholar searches, sorted into 30 areas (taxonomy.py)
python3 02_fulltext.py    # arXiv full texts for at most 80 papers per area (about 1 h; a second copy with `reverse` halves it)
python3 03_people.py      # authors and their earliest works from OpenAlex (needs ~/.config/openalex_key, about 5,400 credits)
python3 04_methods.py     # rule-based coding / maths / compute level per paper (2 min; run in the foreground)
python3 validate_compare.py   # rule vs hand labels in validation/labels.json
python3 05_aggregate.py   # -> site/data.json (people only as counts)
python3 06_build_site.py  # -> site/index.html and site/artifact.html
python3 probe.py <area,area> "<regex>"   # how many full texts of an area mention something (gap checks)
```
`data/` (downloads, caches, the people table with names) is not committed.
`site/shortlist.json` is the worked example (Antonia's three project ideas); delete it for a neutral public copy.

## Open
- Not yet on GitHub and not hosted publicly; published only as a private claude.ai artifact.
- Rendered page not yet checked by eye (screenshots were taken but not reviewed).
- Fellowship alumni (Pivotal, MATS ...) are counted only through paper acknowledgments; LinkedIn was not scraped.
- Method levels agree with hand labels on 61-82% of papers (same level), 83-94% for the reach decision: fine for area shares, rough for single papers.
