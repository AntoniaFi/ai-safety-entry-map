# AI Safety Entry Map

**Which AI-safety research areas can you enter with the skills and hardware you have now?**

Live: **https://antoniafi.github.io/ai-safety-entry-map/**

Set four things (coding with models, maths, compute, and whether you can run studies with people), and the map shows, for 30 research areas:

- the share of recent papers whose methods need no more than your skills,
- how many first authors are new to publishing and how many come from outside computer science,
- papers to build on (filtered by reach, shared code, small open models),
- open questions: sentences in which authors name a limit or something left undone.
- starter projects: 2 to 8 project ideas matched to your levels (papers to replicate or extend, surveys, reviews, tools), each built on papers from the map and quoting the open question it answers (`site/projects.json`).

## Why I built it

I'm a bioprocess scientist (PhD, Wageningen University) moving into AI safety. My first practical question was where someone with my background could do useful research now, not after a year of ML coursework. Reading lists and career guides didn't answer that from the evidence, so I built a map from the papers themselves.

## How it works

| Step | Script | What it does |
|---|---|---|
| 1 | `01_corpus.py` | Collects candidate papers (a daily AI-safety literature sweep plus Semantic Scholar searches) and sorts them into 30 areas by key phrases (`taxonomy.py`) |
| 1b | `01b_observatory.py` | Adds arXiv papers (2022 on) from the [AI Safety Observatory](https://aisafetyobservatory.com)'s Sources log that are not marked out of scope and match an area at least once |
| 2 | `02_fulltext.py` | Downloads arXiv full texts, at most 80 per area (half most cited, half random), plus every paper from step 1b |
| 3 | `03_people.py` | Author histories from OpenAlex: years since first paper, earlier field |
| 4 | `04_methods.py` | Rule-based reading of each full text: method words, model names and sizes, hardware, statistics, code links, acknowledgments → a coding, maths and compute level per paper |
| 5 | `05_aggregate.py` | Aggregates to `site/data.json` (people only as counts per area) |
| 6 | `06_build_site.py` | Builds `docs/index.html` (the live page) from `site/template.html` and `site/projects.json`; checks that every project's papers are in the data and its quotes are word for word |

`harvest/` is the next stage, in progress: a larger store of every AI-safety candidate paper since 2018 from arXiv, OpenAlex and Semantic Scholar, with a classifier (see `harvest/README.md`).

Rules rather than a language model read the papers, so every level can be traced back to the words that set it, and the result is reproducible.

### Run it yourself

```
python3 01_corpus.py
python3 01b_observatory.py      # reads ../AI_Safety_Observatory/content/sources/
python3 02_fulltext.py          # about 1 h
python3 03_people.py            # needs an OpenAlex key in ~/.config/openalex_key
python3 04_methods.py
python3 validate_compare.py     # rule levels vs hand labels in validation/labels.json
python3 05_aggregate.py
python3 06_build_site.py
python3 probe.py <area,area> "<regex>"   # how many full texts of an area mention something
```

Python 3 standard library only. Raw downloads and caches go to `data/`, which is not in the repository.

## How good is it?

The rule levels were compared with Claude's reading of the methods sections of 200 papers read in full, drawn at random within each area, without seeing the rule's answer (`validate_gold_C.py`, labels in `validation/gold_C_labels.json`):

| Skill | Same level | Within one level | Same within-reach decision |
|---|---|---|---|
| Coding | 66% | 96% | 88% |
| Working with ML models | 66% | 88% | 88% |
| Maths | 67% | 98% | 88% |
| Compute | 64% | 88% | 90% |
| Studies with people | 94% | – | 94% |

Good enough for shares per area; rough for any single paper. Compute is the weakest. Its rule was revised on 24 Nov 2026 (hardware named and largest open model run, instead of smallest model named) using the first 100 papers of the sample; on the other 100 it agrees 61% on the same level (89% within one), against 50% before. It still tends to rate papers one level harder than the reading. **The labels were made by Claude, not by a person**, so this is a consistency check, not ground truth. A human-labelled sample is the next step.

Other limits: years since first paper stand in for career stage; only arXiv papers are read in full (forum posts are missed); authors with no earlier papers have no known field; 2026 is a part year.

## How this was made

I wrote the code with Claude Code as coding assistant. The research question, the choice of what to measure, the taxonomy decisions and the checks of the output are mine.

## Licence

Code: MIT (see `LICENSE`). Page text and aggregated data: CC BY 4.0. Paper titles and quoted sentences belong to their authors and link to the source.

## Contact

Antonia Fichtbauer · corrections and ideas welcome as [issues](https://github.com/AntoniaFi/ai-safety-entry-map/issues) · also: [AI Safety Observatory](https://aisafetyobservatory.com), [grasshopping.com](https://grasshopping.com)
