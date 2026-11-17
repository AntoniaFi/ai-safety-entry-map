# Universe harvest: from 3,800 papers to the whole field

Started 17 Nov 2026, after comparing the Entry Map corpus with the Emerging Technology Observatory (ETO) count of about
45,000 AI-safety papers for 2018-2023 (https://eto.tech/blog/still-drop-bucket-ai-safety-research/; their live page says
55,567 for 2019-2024).

## Why ETO counts ten times more
| | ETO | Entry Map corpus (16 Nov) |
|---|---|---|
| Definition | Broad: robustness, explainability, bias mitigation, alignment, monitoring and control, testing and verification, human-AI and multi-agent coordination | 30 areas, mostly modes of misalignment in language models |
| How a paper gets in | A classifier scores every AI paper (their figures: precision 0.73, recall 0.80) | A key phrase in the title, or twice in the abstract |
| Sources | Merged Academic Corpus, 280 million records: The Lens, arXiv, Papers with Code, Semantic Scholar, OpenAlex | Observatory sweep (arXiv, LessWrong, OpenAlex for selected authors) + the first 2,000 Semantic Scholar hits per area |
| Years | 2018 on | 2022 on |
| Languages | English title or abstract | English |

ETO's corpus and classifier are not downloadable, so the pipeline below rebuilds the approach from open sources.

## Pipeline
```
harvest/store.py             one SQLite file, data/universe.sqlite; a work is matched across sources by arXiv id, DOI or title
harvest/arxiv_oai.py         every arXiv paper in 18 AI-related categories since 2018 (free, no login)
harvest/openalex_harvest.py  three OpenAlex topics in full + phrase searches with AI context (key in ~/.config/openalex_key)
harvest/s2_bulk.py           Semantic Scholar bulk search for every phrase list (works without a key; ~/.config/s2_key makes it steady)
harvest/import_local.py      the Observatory sources log and the Entry Map corpus
harvest/queries.py           the phrase lists: 9 broad fields (ETO's scope) + the 30 areas of taxonomy.py
harvest/classify.py          labelling rules -> text classifier -> safety yes/no, fields, areas per record (run with .venv/bin/python)
harvest/gold.py              hand labels, precision and recall, threshold
harvest/run.sh               one daily pass of everything above
```
Daily: `zsh harvest/run.sh` (OpenAlex stops at 4,500 remaining credits so the Observatory's morning sweep keeps its share).

Two tiers come out of the same store: the **broad** tier (comparable with ETO) and the **narrow** tier (the 30 areas).
Nothing is written to the Observatory site; whether and how its Sources page takes records from here is an open decision.

## Access to unlock (in order of gain)
1. **Semantic Scholar API key** (free, a form, key arrives by email): https://www.semanticscholar.org/product/api#api-key-form
   Save it as one line in `~/.config/s2_key`. Without it the bulk search is throttled and can stall.
2. **OpenAlex**: nothing to do; the free key gives 10,000 credits a day and the harvest continues daily until done.
3. **The Lens** (ETO's one commercial source; free for personal research on request): https://www.lens.org/lens/user/subscriptions
   -> Scholarly API -> request access. Save the token in `~/.config/lens_token`. Harvester not written yet (needs the live token to test).
4. **Scopus through WUR** (ends with the WUR account): https://dev.elsevier.com/apikey/manage on the WUR network or VPN.
   Save the key in `~/.config/scopus_key`. Harvester not written yet. Gain: clean journal and proceedings records, few new papers.

Not used: LinkedIn (terms forbid scraping), CNKI (no access; ETO lacks it too), Papers with Code (API closed in 2025).
