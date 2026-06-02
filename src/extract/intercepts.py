"""Phase 5 — extract drill intercepts from report prose into a clean schema.

Turns sentences like
    "Drill hole PBNC1285 returned 6 metres @ 5.36 g/t Au, from 236 to 242 metres downhole."
into structured records:
    {anumber, page, hole, interval_m, grade, element, from_m, to_m, source}

Designed for the format variants this corpus actually contains: '@' vs 'at', 'g/t' with or
without a space, decimal depths, 'from X to Y m' or 'from X m', and missing fields. We FAIL
GRACEFULLY — leave a field null rather than invent it — and keep the source snippet + page so
every extracted number is verifiable/citable.

Run:  python -m src.extract.intercepts            # extract corpus -> data/processed/intercepts.csv
      python -m src.extract.intercepts --selftest # check patterns on known strings
"""
from __future__ import annotations

import csv
import json
import re
import sys

from src import config as C

PAGES = C.INTERIM / "pages.jsonl"
OUT = C.PROCESSED / "intercepts.csv"

# core intercept pattern: <interval> m @/at <grade> g/t <element?> [from <a> to <b> m]
INTERCEPT_RE = re.compile(
    r"(?P<interval>\d+(?:\.\d+)?)\s*m(?:etres?)?\b\s*(?:@|\bat\b)\s*"
    r"(?P<grade>\d+(?:\.\d+)?)\s*g\s*/?\s*t\s*"
    r"(?P<element>Au|Cu|Ni|Ag|Co|Zn|Pb|Sn|Li)?"
    r"(?:[^.\n]{0,40}?from\s*(?P<from>\d+(?:\.\d+)?)\s*"
    r"(?:(?:to|[-–−])\s*(?P<to>\d+(?:\.\d+)?))?\s*m)?",
    re.I,
)
HOLE_RE = re.compile(r"\b([A-Z]{2,5}\d{2,5}[A-Z]?)\b")


def _num(x):
    return float(x) if x is not None else None


def extract(text: str):
    rows = []
    for m in INTERCEPT_RE.finditer(text):
        # nearest drill-hole code in the ~70 chars before the match
        pre = text[max(0, m.start() - 70): m.start()]
        holes = HOLE_RE.findall(pre)
        hole = holes[-1] if holes else None
        snippet = " ".join(text[max(0, m.start() - 40): m.end() + 10].split())
        rows.append({
            "hole": hole,
            "interval_m": _num(m.group("interval")),
            "grade": _num(m.group("grade")),
            "element": (m.group("element") or "Au").title(),
            "from_m": _num(m.group("from")),
            "to_m": _num(m.group("to")),
            "source": snippet,
        })
    return rows


SELFTEST = [
    "Drill hole PBNC1285 returned 6 metres @ 5.36 g/t Au, from 236 to 242 metres downhole.",
    "PBND0204, 0.5 metres @ 5.98g/t Au from 180.6 to 181.1 metres downhole",
    "PBNC1241 intersected 27 metres @ 1.68 g/t Au",
    "the peak result was 0.65 m at 0.09 g/t Au from 44.35 m",
]


def selftest() -> None:
    for s in SELFTEST:
        r = extract(s)
        print(f"IN : {s}\nOUT: {r}\n")


def main(argv) -> None:
    if "--selftest" in argv:
        selftest()
        return
    pages = [json.loads(l) for l in PAGES.open(encoding="utf-8")]
    rows = []
    for p in pages:
        for r in extract(p["text"]):
            rows.append({"anumber": p["anumber"], "page": p["page"], **r})

    cols = ["anumber", "page", "hole", "interval_m", "grade", "element", "from_m", "to_m", "source"]
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader(); w.writerows(rows)

    reports = {r["anumber"] for r in rows}
    with_depth = sum(r["from_m"] is not None for r in rows)
    with_hole = sum(r["hole"] is not None for r in rows)
    print(f"[ok] {len(rows)} intercepts from {len(reports)} report(s) -> {OUT}")
    print(f"     with drill-hole id: {with_hole} | with depth interval: {with_depth}")
    print("\nsample (verify these against the source text):")
    for r in rows[:15]:
        d = f"{r['from_m']}-{r['to_m']}m" if r["from_m"] is not None else "depth n/a"
        print(f"  A{r['anumber']} p{r['page']:>3} {str(r['hole']):10s} "
              f"{r['interval_m']}m @ {r['grade']} g/t {r['element']:3s} ({d})")


if __name__ == "__main__":
    main(sys.argv[1:])
