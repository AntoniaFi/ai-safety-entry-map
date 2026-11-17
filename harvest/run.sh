#!/bin/zsh
# One pass of the universe harvest: new arXiv months, the next slice of OpenAlex within the day's credits, Semantic Scholar, then re-label.
# Safe to run every day; each step continues where it stopped.   Usage: zsh harvest/run.sh [openalex reserve, default 4500]
cd "$(dirname "$0")"
python3 -u arxiv_oai.py        | tee -a ../data/harvest_arxiv.log
python3 -u openalex_harvest.py all ${1:-4500} | tee -a ../data/harvest_openalex.log
python3 -u s2_bulk.py          | tee -a ../data/harvest_s2.log
cd .. && .venv/bin/python harvest/classify.py && python3 harvest/gold.py eval
