"""Score task runs against the marking scheme.

Measurement aspects are checked automatically. Judgement aspects come from the panel's blind
ratings in ratings/<task>/ratings.csv, mapped back to runs through ratings/<task>/key.json; until
the panel has rated, they are reported as pending.

Usage:
    python -m harness.score CON-01
"""

import argparse
import csv
import json
from collections import defaultdict
from statistics import mean

import krippendorff
import numpy as np
import yaml

from harness.models import REPO_ROOT

IDS = ["C1", "C2", "C3", "C4", "C5", "C6"]
CABLE_WORDS = ("cable", "conductor", "cross-section", "cross sectional", "csa", "mm²", "mm2")
RCD_WORDS = ("rcd", "residual current")
EFFORT_ORDER = ["minimal", "low", "medium", "high"]


def _first(steps, kind):
    return next((i for i, s in enumerate(steps) if s["kind"] == kind), None)


def _positions(steps, test):
    # Any step kind counts, so a test attached to the energize step is read as done at energization.
    return [i for i, s in enumerate(steps) if s["test"] == test]


def measure(run, key):
    """Return {aspect_id: passed} for every measurement aspect."""
    circuits = {c["id"]: c for c in run["plan"]["circuits"]}
    steps = sorted(run["plan"]["sequence"], key=lambda s: s["step"])
    change, new = run["change"], key["change_circuit"]
    energize = _first(steps, "energize")
    isolation, installation = _first(steps, "safe_isolation"), _first(steps, "installation")

    def every(check):
        return all(
            cid in circuits
            and check(circuits[cid], key["circuits"][cid], key["specification"][key["circuits"][cid]["circuit_type"]])
            for cid in IDS
        )

    def flagged(cid, words):
        circuit = circuits.get(cid, {})
        return circuit.get("compliant") is False and any(w in (circuit.get("issue") or "").lower() for w in words)

    return {
        "PE-M1": set(circuits) == set(IDS) and every(lambda got, exp, req: got["circuit_type"] == exp["circuit_type"]),
        "PE-M2": every(lambda got, exp, req: (got["mcb_rating_a_as_drawn"], got["cable_mm2_as_drawn"])
                       == (exp["mcb_as_drawn"], exp["cable_as_drawn"])),
        "PE-M3": every(lambda got, exp, req: got["rcd_protected_as_drawn"] == exp["rcd_as_drawn"]),
        "TC-M1": every(lambda got, exp, req: (got["required_mcb_rating_a"], got["required_cable_mm2"])
                       == (req["mcb"], req["cable"])),
        "TC-M2": every(lambda got, exp, req: got["rcd_required"] == req["rcd"]),
        "SC-M1": flagged("C5", CABLE_WORDS),
        "SC-M2": flagged("C6", RCD_WORDS),
        "SC-M3": all(circuits.get(cid, {}).get("compliant") is True for cid in IDS[:4]),
        "PC-M1": None not in (isolation, installation) and isolation < installation,
        "PC-M2": energize is not None
        and all(any(p < energize for p in _positions(steps, t)) for t in key["dead_tests"])
        and all(_positions(steps, t) for t in key["order_free_tests"]),
        "PC-M3": energize is not None
        and all(_positions(steps, t) and min(_positions(steps, t)) >= energize for t in key["live_tests"]),
        "AD-M1": (change["id"], change["circuit_type"], change["required_mcb_rating_a"],
                  change["required_cable_mm2"], change["rcd_required"])
        == (new["id"], new["circuit_type"], new["mcb"], new["cable"], new["rcd"]),
        "AD-M2": set(key["dead_tests"] + key["live_tests"] + key["order_free_tests"]) <= set(change["tests"]),
    }


def load_ratings(task_id):
    """Return {(run, aspect): {rater: score}} from the panel's blind ratings, if any."""
    folder = REPO_ROOT / "ratings" / task_id
    if not (folder / "ratings.csv").exists():
        return {}
    key = json.loads((folder / "key.json").read_text(encoding="utf-8"))
    ratings = defaultdict(dict)
    with open(folder / "ratings.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["score"].strip():
                ratings[(key[row["plan"]], row["aspect"])][row["rater"]] = int(row["score"])
    return ratings


def agreement(ratings):
    """Krippendorff's alpha (ordinal) and the share of rated units whose scores span at most one point."""
    units = sorted(ratings)
    raters = sorted({r for scores in ratings.values() for r in scores})
    data = np.array([[ratings[u].get(r, np.nan) for u in units] for r in raters], dtype=float)
    varied = len(np.unique(data[~np.isnan(data)])) > 1
    alpha = krippendorff.alpha(reliability_data=data, level_of_measurement="ordinal") if varied else None
    within_one = mean(max(s.values()) - min(s.values()) <= 1 for s in ratings.values())
    return alpha, within_one


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("task_id")
    args = parser.parse_args()

    scheme = yaml.safe_load((REPO_ROOT / "tasks" / args.task_id / "marking_scheme.yaml").read_text(encoding="utf-8"))
    weights = yaml.safe_load((REPO_ROOT / "rubric" / "dimensions.yaml").read_text(encoding="utf-8"))["dimensions"]
    in_scope = {d: w["weight"] for d, w in weights.items() if d not in scheme["out_of_scope"]}
    marks_by_dimension = defaultdict(int)
    for aspect in scheme["aspects"]:
        marks_by_dimension[aspect["dimension"]] += aspect["marks"]
    assert marks_by_dimension == in_scope, f"aspect marks {dict(marks_by_dimension)} differ from weights {in_scope}"

    measured = [a for a in scheme["aspects"] if a["type"] == "measurement"]
    judged = [a for a in scheme["aspects"] if a["type"] == "judgement"]
    ratings = load_ratings(args.task_id)

    rows = []
    for path in sorted((REPO_ROOT / "runs" / args.task_id).glob("*.json")):
        run = json.loads(path.read_text(encoding="utf-8"))
        passed = measure(run, scheme["answer_key"])
        marks = {a["id"]: a["marks"] * passed[a["id"]] for a in measured}
        for a in judged:
            if scores := ratings.get((path.stem, a["id"])):
                marks[a["id"]] = a["marks"] * mean(scores.values()) / 3
        rows.append({
            "run": path.stem,
            "effort": run["reasoning_effort"],
            "sample": run["sample"],
            **{a["id"]: round(marks[a["id"]], 2) if a["id"] in marks else "pending" for a in scheme["aspects"]},
            "measurement": sum(marks[a["id"]] for a in measured),
            "reasoning_tokens": sum(u["reasoning_tokens"] for u in run["usage"].values()),
            "total": round(sum(marks.values()) / sum(in_scope.values()) * 100, 1)
            if len(marks) == len(scheme["aspects"]) else "pending",
        })

    out_dir = REPO_ROOT / "results" / args.task_id
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "scores.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    efforts = sorted({r["effort"] for r in rows}, key=EFFORT_ORDER.index)
    groups = [[r for r in rows if r["effort"] == e] for e in efforts]

    def spread(label, marks, key):
        cells = []
        for g in groups:
            values = [r[key] for r in g]
            cells.append("pending" if "pending" in values
                         else f"{mean(values):.1f} [{min(values):.1f}, {max(values):.1f}]")
        return f"| {label}, mean [min, max] | {marks} | {' | '.join(cells)} |"

    lines = [
        f"| Aspect | Marks | {' | '.join(efforts)} |",
        f"|---|---|{'---|' * len(efforts)}",
        *(f"| {a['id']} | {a['marks']} | " + " | ".join(f"{sum(r[a['id']] > 0 for r in g)}/{len(g)}" for g in groups) + " |"
          for a in measured),
        spread("Measurement marks", sum(a["marks"] for a in measured), "measurement"),
        *(spread(a["id"], a["marks"], a["id"]) for a in judged),
        spread("Total, renormalized", 100, "total"),
        "| Reasoning tokens, mean | | " + " | ".join(f"{mean(r['reasoning_tokens'] for r in g):.0f}" for g in groups) + " |",
    ]
    if ratings:
        alpha, within_one = agreement(ratings)
        by_rater = defaultdict(list)
        for scores in ratings.values():
            for rater, score in scores.items():
                by_rater[rater].append(score)
        lines += ["", f"Judgement agreement: Krippendorff's alpha (ordinal) = "
                      f"{'undefined' if alpha is None else f'{alpha:.2f}'}; "
                      f"scores within one point on {within_one:.0%} of rated aspects.",
                  "Mean score by rater: " + ", ".join(f"{r} {mean(s):.2f}" for r, s in sorted(by_rater.items()))]
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
