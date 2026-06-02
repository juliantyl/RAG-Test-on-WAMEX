"""Phase 4 — retrieval evaluation: semantic vs lexical vs hybrid.

"It returned an answer" is not evidence. We measure whether the chunk that actually contains
the answer lands in the top-k, across a labelled question set.

  recall@k = fraction of questions whose answer chunk appears in the top-k results.
  MRR      = mean of 1/(rank of first correct chunk); rewards ranking the answer high.

A retrieved chunk is "correct" if its text matches the question's `verify` regex (the answer
fingerprint). We sanity-check first that the corpus actually contains a matching chunk — a
question whose answer isn't in the corpus would be an unfair/broken label.

Run:  python -m src.eval.evaluate
"""
from __future__ import annotations

import json
import re

import numpy as np

from src import config as C
from src.index.retrieve import Retriever

QUESTIONS = (C.ROOT / "src" / "eval" / "questions.jsonl")
KS = (1, 3, 5, 10)
N = 10               # depth retrieved per method
RRF_K = 60


def fuse(sem, lex):
    """Reciprocal Rank Fusion of two ranked index lists -> fused ranked index list."""
    s = {}
    for rank, i in enumerate(sem):
        s[i] = s.get(i, 0.0) + 1.0 / (RRF_K + rank)
    for rank, i in enumerate(lex):
        s[i] = s.get(i, 0.0) + 1.0 / (RRF_K + rank)
    return sorted(s, key=s.get, reverse=True)


def first_correct_rank(R, indices, verify) -> int | None:
    rx = re.compile(verify, re.I)
    for rank, i in enumerate(indices, 1):
        if rx.search(R.chunks[i]["text"]):
            return rank
    return None


def main() -> None:
    qs = [json.loads(l) for l in QUESTIONS.open(encoding="utf-8")]
    R = Retriever()

    # label sanity check: is each answer actually present in the corpus?
    bad = []
    for q in qs:
        rx = re.compile(q["verify"], re.I)
        if not any(rx.search(c["text"]) for c in R.chunks):
            bad.append(q["id"])
    if bad:
        print(f"WARNING: no corpus chunk matches verify for question ids {bad} (label issue)\n")

    methods = ("semantic", "lexical", "hybrid")
    ranks = {m: [] for m in methods}
    for q in qs:
        sem = R._semantic_rank(q["question"], N)
        lex = R._lexical_rank(q["question"], N)
        idx = {"semantic": sem, "lexical": lex, "hybrid": fuse(sem, lex)}
        for m in methods:
            ranks[m].append(first_correct_rank(R, idx[m], q["verify"]))

    # report
    hdr = f"{'method':10s}" + "".join(f"  R@{k:<3}" for k in KS) + f"  {'MRR':>5s}"
    print(f"Retrieval evaluation on {len(qs)} labelled questions (depth N={N})\n")
    print(hdr); print("-" * len(hdr))
    for m in methods:
        rk = ranks[m]
        row = f"{m:10s}"
        for k in KS:
            row += f"  {np.mean([r is not None and r <= k for r in rk]):.2f} "
        mrr = np.mean([1.0 / r if r else 0.0 for r in rk])
        row += f"  {mrr:.3f}"
        print(row)

    # per-kind hybrid breakdown (where each method helps)
    print("\nfirst-correct rank by question (lower = better; '-' = missed in top N):")
    print(f"{'id':>3} {'kind':11s} {'sem':>4} {'lex':>4} {'hyb':>4}  question")
    for n, q in enumerate(qs):
        def r(m):
            v = ranks[m][n]; return str(v) if v else "-"
        print(f"{q['id']:>3} {q['kind']:11s} {r('semantic'):>4} {r('lexical'):>4} {r('hybrid'):>4}  {q['question'][:54]}")


if __name__ == "__main__":
    main()
