# Haplopraxis Analysis Tools (NumPy + SymPy + NLTK)

Repository-specific NLP and structural analysis scripts for `standardgalactic/haplopraxis`.

## File

- `/home/runner/work/haplopraxis/haplopraxis/analysis-tools/haplopraxis_analysis.py`

## What it analyzes

1. **Corpus analysis** (`corpus`)
   - Canonical texts:
     - `/home/runner/work/haplopraxis/haplopraxis/README.md`
     - `/home/runner/work/haplopraxis/haplopraxis/haplopraxis-design-document.md`
     - `/home/runner/work/haplopraxis/haplopraxis/urfn-ccfa-constitutional-spec.md`
     - `/home/runner/work/haplopraxis/haplopraxis/under-construction/developmental-opacity.tex`
   - Computes lexical diversity and entropy with **NumPy**.
   - Computes a symbolic/derived opacity indicator with **SymPy**.
   - Produces repository strata counts from the current tree.

2. **Word-list overlap** (`overlap`)
   - Uses repository corpora:
     - `/home/runner/work/haplopraxis/haplopraxis/Random-words.txt`
     - `/home/runner/work/haplopraxis/haplopraxis/Sight-words.txt`
     - `/home/runner/work/haplopraxis/haplopraxis/Wikipedia-watchlist.txt`
   - Produces a pairwise Jaccard similarity matrix via **NumPy**.

3. **Lineage analysis** (`lineage`)
   - Reads `/home/runner/work/haplopraxis/haplopraxis/sample-lineage.json`.
   - Builds event-transition probabilities with **NumPy**.
   - Solves symbolic stationary distribution with **SymPy**.

4. **Phrase mining** (`phrases`)
   - Extracts high-PMI domain bigrams from canonical docs with **NLTK**.

## Install dependencies

```bash
pip install numpy sympy nltk
```

## Usage

From repository root (`/home/runner/work/haplopraxis/haplopraxis`):

```bash
python analysis-tools/haplopraxis_analysis.py corpus
python analysis-tools/haplopraxis_analysis.py overlap
python analysis-tools/haplopraxis_analysis.py lineage
python analysis-tools/haplopraxis_analysis.py phrases --top-n 40
python analysis-tools/haplopraxis_analysis.py all --output /tmp/haplopraxis-analysis.json
```

All commands print JSON to stdout unless `--output` is provided.
