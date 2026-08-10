#!/usr/bin/env python3
"""Repository-specific NumPy/SymPy/NLTK analysis tools for Haplopraxis."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import sympy as sp

try:
    import nltk
    from nltk.collocations import BigramAssocMeasures, BigramCollocationFinder
except Exception as exc:  # pragma: no cover - runtime environment dependent
    raise SystemExit(
        "NLTK is required. Install dependencies with: pip install nltk numpy sympy"
    ) from exc

ROOT = Path(__file__).resolve().parents[1]

CANONICAL_TEXT_FILES = {
    "readme": ROOT / "README.md",
    "design": ROOT / "haplopraxis-design-document.md",
    "constitution": ROOT / "urfn-ccfa-constitutional-spec.md",
    "opacity": ROOT / "under-construction" / "developmental-opacity.tex",
}

CANONICAL_WORD_LISTS = {
    "random_words": ROOT / "Random-words.txt",
    "sight_words": ROOT / "Sight-words.txt",
    "wikipedia_watchlist": ROOT / "Wikipedia-watchlist.txt",
}

CANONICAL_LINEAGE = ROOT / "sample-lineage.json"

STOPWORDS = {
    "the", "and", "to", "of", "a", "in", "is", "for", "that", "as", "on", "with", "it", "this",
    "are", "be", "or", "by", "an", "from", "at", "not", "can", "all", "their", "into", "more",
    "than", "which", "its", "has", "have", "also", "through", "these", "but", "was", "were",
}


def ensure_nltk_resource(resource_name: str, path_hint: str) -> None:
    try:
        nltk.data.find(path_hint)
    except LookupError:
        nltk.download(resource_name, quiet=True)


def normalize_text(text: str) -> str:
    return text.replace("\u2014", " ").replace("\u2013", " ").lower()


def words(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z\-']*", normalize_text(text))


def sentence_tokenize(text: str) -> list[str]:
    ensure_nltk_resource("punkt", "tokenizers/punkt")
    ensure_nltk_resource("punkt_tab", "tokenizers/punkt_tab/english")
    return nltk.sent_tokenize(text)


def lexical_metrics(tokens: Sequence[str]) -> dict[str, float | int]:
    if not tokens:
        return {
            "token_count": 0,
            "type_count": 0,
            "type_token_ratio": 0.0,
            "shannon_entropy_bits": 0.0,
            "simpson_diversity": 0.0,
        }
    counts = np.array(list(Counter(tokens).values()), dtype=float)
    probs = counts / counts.sum()
    entropy = float(-np.sum(probs * np.log2(probs)))
    simpson = float(1.0 - np.sum(probs**2))
    return {
        "token_count": int(len(tokens)),
        "type_count": int(len(set(tokens))),
        "type_token_ratio": float(len(set(tokens)) / len(tokens)),
        "shannon_entropy_bits": entropy,
        "simpson_diversity": simpson,
    }


def top_content_words(tokens: Sequence[str], limit: int = 25) -> list[tuple[str, int]]:
    filtered = [t for t in tokens if t not in STOPWORDS and len(t) > 2]
    return Counter(filtered).most_common(limit)


def symbolic_opacity_index(history_depth: int, visible_surface_files: int, strata_files: int) -> str:
    h, v, s = sp.symbols("h v s", positive=True)
    expr = sp.log(1 + h + s) / sp.log(2 + v)
    value = expr.subs({h: history_depth, v: max(1, visible_surface_files), s: max(1, strata_files)})
    return str(sp.N(value, 8))


def classify_repository_strata(path: Path) -> str:
    p = str(path.relative_to(ROOT))
    if p in {"README.md", "index.html", "game.js", "styles.css", "sample-lineage.json"}:
        return "playable-surface"
    if p.endswith(".md") and ("design" in p or "constitutional" in p):
        return "theory-docs"
    if any(k in p.lower() for k in ["watchlist", "wikipedia", "random-words", "sight-words"]):
        return "corpus-data"
    if any(k in p.lower() for k in ["sga", "galactic", "fonts"]):
        return "script-font-layer"
    return "archive-strata"


def scan_strata_counts() -> dict[str, int]:
    counts: Counter[str] = Counter()
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if ".git" in path.parts:
            continue
        counts[classify_repository_strata(path)] += 1
    return dict(sorted(counts.items(), key=lambda kv: kv[0]))


def analyze_corpus() -> dict:
    docs: dict[str, dict] = {}
    merged_tokens: list[str] = []

    for label, path in CANONICAL_TEXT_FILES.items():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        tokens = words(text)
        merged_tokens.extend(tokens)
        docs[label] = {
            "path": str(path),
            "metrics": lexical_metrics(tokens),
            "top_content_words": top_content_words(tokens, 20),
            "sentence_count": len(sentence_tokenize(text)),
        }

    strata_counts = scan_strata_counts()
    total_files = sum(strata_counts.values())
    opacity_index = symbolic_opacity_index(
        history_depth=int(total_files),
        visible_surface_files=5,
        strata_files=int(total_files - strata_counts.get("playable-surface", 0)),
    )

    return {
        "documents": docs,
        "merged_metrics": lexical_metrics(merged_tokens),
        "merged_top_content_words": top_content_words(merged_tokens, 30),
        "repository_strata_counts": strata_counts,
        "symbolic_opacity_index": opacity_index,
    }


def load_wordlist(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip().lower() for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]


def analyze_wordlist_overlap() -> dict:
    lists = {name: load_wordlist(path) for name, path in CANONICAL_WORD_LISTS.items()}
    sets = {name: set(vals) for name, vals in lists.items()}

    names = list(sets.keys())
    matrix = np.zeros((len(names), len(names)), dtype=float)
    for i, n1 in enumerate(names):
        for j, n2 in enumerate(names):
            denom = len(sets[n1] | sets[n2]) or 1
            matrix[i, j] = len(sets[n1] & sets[n2]) / denom

    return {
        "counts": {name: len(vals) for name, vals in lists.items()},
        "jaccard_similarity_matrix": {
            "labels": names,
            "values": matrix.round(6).tolist(),
        },
        "shared_terms_random_and_sight": sorted(list(sets.get("random_words", set()) & sets.get("sight_words", set())))[:100],
    }


def lineage_transition_matrix(events: Sequence[str]) -> tuple[list[str], np.ndarray]:
    states = sorted(set(events))
    idx = {s: i for i, s in enumerate(states)}
    mat = np.zeros((len(states), len(states)), dtype=float)
    for a, b in zip(events, events[1:]):
        mat[idx[a], idx[b]] += 1.0
    row_sums = mat.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    return states, mat / row_sums


def symbolic_stationary_distribution(states: Sequence[str], p: np.ndarray) -> dict[str, str]:
    if p.size == 0:
        return {}
    P = sp.Matrix(p)
    n = P.rows
    x = sp.symbols(f"x0:{n}")
    vec = sp.Matrix(x)
    equations = list((vec.T * P - vec.T)[0, :])
    equations.append(sum(x) - 1)
    solved = sp.solve(equations, list(x), dict=True)
    if not solved:
        return {state: "0" for state in states}
    sol = solved[0]
    return {state: str(sp.nsimplify(sol.get(xi, 0))) for state, xi in zip(states, x)}


def analyze_lineage(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Lineage file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    events = [entry.get("type", "UNKNOWN") for entry in data if isinstance(entry, dict)]
    labels = [entry.get("label", "") for entry in data if isinstance(entry, dict)]

    states, transition = lineage_transition_matrix(events)
    transition_counts = Counter(zip(events, events[1:]))
    symbolic_pi = symbolic_stationary_distribution(states, transition)

    return {
        "path": str(path),
        "event_count": len(events),
        "event_type_counts": dict(Counter(events)),
        "most_common_label_prefixes": Counter(label.split(":")[0] for label in labels if label).most_common(10),
        "transition_probabilities": {
            "states": states,
            "matrix": transition.round(6).tolist(),
        },
        "transition_counts": [{"from": a, "to": b, "count": c} for (a, b), c in transition_counts.most_common()],
        "symbolic_stationary_distribution": symbolic_pi,
    }


def analyze_phrases(text_paths: Iterable[Path], top_n: int = 25) -> dict:
    ensure_nltk_resource("punkt", "tokenizers/punkt")
    tokens: list[str] = []
    for path in text_paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        tokens.extend(words(text))

    if not tokens:
        return {"bigrams": []}

    finder = BigramCollocationFinder.from_words(tokens)
    finder.apply_word_filter(lambda w: len(w) < 3 or w in STOPWORDS)
    finder.apply_freq_filter(2)
    scored = finder.score_ngrams(BigramAssocMeasures().pmi)

    return {
        "bigrams": [
            {"phrase": f"{a} {b}", "pmi": round(float(score), 6)}
            for (a, b), score in scored[:top_n]
        ]
    }


def write_json(output_path: Path | None, payload: dict) -> None:
    if output_path is None:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Haplopraxis repository analysis toolkit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    corpus = subparsers.add_parser("corpus", help="Analyze canonical theoretical/game text corpus")
    corpus.add_argument("--output", type=Path, default=None)

    overlap = subparsers.add_parser("overlap", help="Analyze overlap among repository word lists")
    overlap.add_argument("--output", type=Path, default=None)

    lineage = subparsers.add_parser("lineage", help="Analyze lineage event sequence with NumPy/SymPy")
    lineage.add_argument("--path", type=Path, default=CANONICAL_LINEAGE)
    lineage.add_argument("--output", type=Path, default=None)

    phrases = subparsers.add_parser("phrases", help="Extract domain bigrams with NLTK PMI")
    phrases.add_argument("--output", type=Path, default=None)
    phrases.add_argument("--top-n", type=int, default=25)

    all_cmd = subparsers.add_parser("all", help="Run all analyses")
    all_cmd.add_argument("--output", type=Path, default=None)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "corpus":
        write_json(args.output, analyze_corpus())
        return
    if args.command == "overlap":
        write_json(args.output, analyze_wordlist_overlap())
        return
    if args.command == "lineage":
        write_json(args.output, analyze_lineage(args.path))
        return
    if args.command == "phrases":
        paths = [
            CANONICAL_TEXT_FILES["readme"],
            CANONICAL_TEXT_FILES["design"],
            CANONICAL_TEXT_FILES["constitution"],
        ]
        write_json(args.output, analyze_phrases(paths, top_n=args.top_n))
        return
    if args.command == "all":
        payload = {
            "corpus": analyze_corpus(),
            "overlap": analyze_wordlist_overlap(),
            "lineage": analyze_lineage(CANONICAL_LINEAGE),
            "phrases": analyze_phrases(
                [
                    CANONICAL_TEXT_FILES["readme"],
                    CANONICAL_TEXT_FILES["design"],
                    CANONICAL_TEXT_FILES["constitution"],
                ]
            ),
        }
        write_json(args.output, payload)
        return

    parser.error("Unknown command")


if __name__ == "__main__":
    main()
