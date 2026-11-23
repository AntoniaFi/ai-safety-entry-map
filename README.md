# AI Safety Entry Map

**Which AI-safety research areas can you enter with the skills and hardware you have now?**

Live: **https://antoniafi.github.io/ai-safety-entry-map/**

Set your level in five skills, and the map shows, for 30 research areas:

- the share of recent papers whose methods need no more than your skills,
- how many first authors are new to publishing and how many come from outside computer science,
- papers to build on (filtered by reach, shared code, small open models),
- open questions: sentences in which authors name a limit or something left undone,
- starter projects: 2 to 8 project ideas matched to your levels (papers to replicate or extend, surveys, reviews, tools), each built on papers from the map and quoting the open question it answers.

## Using the map

**1. Set your skills.** Pick a preset (Scientist new to ML, Social scientist, Software engineer, Mathematician or physicist, Philosopher or writer, ML engineer) or set each skill yourself. The circled **?** next to a level explains it. Your choice is remembered in your browser only.

| Skill | Levels |
|---|---|
| Coding | 0 none · 1 scripts (Python or R, prompting a model through an API) · 2 research software (pipelines, agent scaffolds, PyTorch or Hugging Face) · 3 large systems (training loops, reinforcement learning, many GPUs) |
| Working with ML models | 0 none · 1 use a model as given (chat or API, including fine-tuning through a company's service) · 2 run and fine-tune open models · 3 work inside the model (probes, steering vectors) · 4 build training methods (sparse autoencoders, circuits, reinforcement learning, training from scratch) |
| Maths | 0 no formal maths · 1 applied statistics · 2 linear algebra and optimisation · 3 theorems and proofs |
| Compute | 0 a laptop · 1 a chat subscription · 2 API credits · 3 one consumer GPU (12–24 GB) · 4 rented data-centre GPUs (such as A100 or H100, fewer than eight) · 5 a cluster |
| Studies with people | 0 no · 1 you can run surveys, interviews or experiments with participants |

Every combination can be selected. For unusual ones (for example API credits without any coding) the Starter Projects tab has no cases, so its Apply button is greyed out.

**2. Read the tabs.**

- **Research areas**: one row per area with the share of its papers within your reach, who publishes there, and which methods are common. Click a row for the area's papers and details.
- **Starter Projects**: click Apply for project ideas at your levels, each with papers to start from, steps, the open question it answers and what to watch out for. Below them, an analysis of your levels: where you have the most reach and which skill would open the most papers.
- **Papers to build on**: papers read in full, filterable by area, by reach, by shared code and by use of an open model of 9B parameters or less. Each shows the levels it needs and, where known, short career lines of its authors.
- **Open questions**: sentences from the papers that name a limit or something left undone, searchable by area and text.
- **Method**: how the map is made, the check against hand labels, and its limits.

**3. Read the numbers as shares, not verdicts.** A paper is within reach when none of its levels is above yours. The levels are set by rules from each paper's text and are right for about two in three papers (see *How good is it?*), so shares per area are more reliable than the level of any single paper. Open a paper before deciding that it is out of reach.

## Why I built it

I'm a bioprocess scientist (PhD, Wageningen University) moving into AI safety. My first practical question was where someone with my background could do useful research now, not after a year of ML coursework. Reading lists and career guides didn't answer that from the evidence, so I built a map from the papers themselves.

## How it works

| Step | Script | What it does |
|---|---|---|
| 1 | `01_corpus_store.py` | Takes candidate papers from the universe store (`harvest/`) and sorts them into 30 areas by key phrases (`taxonomy.py`). `01_corpus.py` is the earlier version built on Semantic Scholar searches |
| 1b | `01b_observatory.py` | Adds arXiv papers (2022 on) from the [AI Safety Observatory](https://aisafetyobservatory.com)'s Sources log that are not marked out of scope and match an area at least once |
| 2 | `02_fulltext.py` | Downloads arXiv full texts, at most 80 per area (half most cited, half random), plus every paper from step 1b |
| 3 | `03_people.py`, `03b_careers.py` | Author histories from OpenAlex: years since first paper, earlier field; short career lines for authors of papers read in full |
| 4 | `04_methods.py` | Rule-based reading of each full text: method words, model names and sizes, hardware, statistics, code links, acknowledgments → five levels per paper (coding and working with ML models are split in `05_aggregate.py`) |
| 5 | `05_aggregate.py` | Aggregates to `site/data.json` (people only as counts per area) |
| 6 | `06_build_site.py` | Builds `docs/index.html` (the live page) from `site/template.html` and `site/projects.json`; checks that every project's papers are in the data and its quotes are word for word |

### What the numbers rest on

- **Which papers.** Candidates come from a store of over a million papers (arXiv in 18 AI-related categories, plus OpenAlex and Semantic Scholar searches for AI-safety phrases) and from the AI Safety Observatory's Sources log. A paper belongs to an area when the area's key phrases appear in its title or at least twice in its abstract (once for Observatory papers, which are already vetted). Papers from 2022 on; papers neither on arXiv nor cited at least three times are left out. The phrases for each area are in `taxonomy.py`.
- **Which papers are read in full.** Only arXiv papers with an HTML version: at most 80 per area (half the most cited, half at random) plus every Observatory paper. All shares of "within reach" are shares of these papers, not of every paper in the area.
- **How levels are set.** `04_methods.py` cuts the reference list and counts words in the rest: methods, model names and sizes, hardware, statistics, theorems, code links. Compute follows the hardware a paper names and the largest open model it runs; prompting-only work on open models above 120B counts as API credits, since such models are usually served through an API. Each paper's levels and the rule's reasons are recorded in `data/methods.json`, so a level can be traced to the words that set it.
- **People.** Author histories come from OpenAlex: years since a person's first paper (a stand-in for career stage) and the field of their earlier papers. People appear only as counts per area; names show only as public career lines under papers.
- **Starter projects.** Curated in `site/projects.json`, not generated by the rules. Each needs list uses the same five skills. The build (`06_build_site.py`) stops if a project cites a paper that is not in the map or quotes a sentence that is not word for word in that paper's open questions.

`harvest/` is the next stage, in progress: a larger store of every AI-safety candidate paper since 2018 from arXiv, OpenAlex and Semantic Scholar, with a classifier (see `harvest/README.md`).

Rules rather than a language model read the papers, so every level can be traced back to the words that set it, and the result is reproducible.

### Run it yourself

```
python3 01_corpus_store.py      # needs data/universe.sqlite from harvest/
python3 01b_observatory.py      # reads ../AI_Safety_Observatory/content/sources/
python3 02_fulltext.py          # about 1 h
python3 03_people.py            # needs an OpenAlex key in ~/.config/openalex_key
python3 03b_careers.py
python3 04_methods.py
python3 validate_gold_C.py compare   # rule levels vs the 200 hand labels in validation/gold_C_labels.json
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
