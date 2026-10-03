"""Build a blind rating packet for the judgement aspects of a task.

Takes the runs of the chosen samples (sample 1 of each configuration by default), shuffles them
under neutral labels, and writes to ratings/<task>/:
    packet.md     task materials, judgement aspects with benchmarks, and the plans, for the panel
    packet.html   the same as a single self-contained file, with the drawing embedded
    ratings.csv   rating sheet with one row per plan, aspect, and rater
    key.json      label to run mapping, withheld from the panel until ratings are recorded

Labels are reshuffled on every run, so do not regenerate a packet once it has been sent.

Usage:
    python -m harness.rater_packet CON-01 --samples 1 2 3 --raters R1 R2 R3
"""

import argparse
import base64
import csv
import json
import random
import shutil
from string import ascii_uppercase

import markdown
import yaml

from harness.models import REPO_ROOT

STYLE = """
body { font: 15px/1.5 system-ui, sans-serif; max-width: 60rem; margin: 2rem auto; padding: 0 1rem; color: #222; }
table { border-collapse: collapse; margin: 1rem 0; }
th, td { border: 1px solid #bbb; padding: 0.3rem 0.6rem; text-align: left; vertical-align: top; }
img { max-width: 100%; }
blockquote { border-left: 3px solid #bbb; margin-left: 0; padding-left: 1rem; color: #444; }
h2 { border-top: 1px solid #ddd; padding-top: 1rem; }
"""


def _rcd(flag, yes, no):
    return yes if flag else no


def render_plan(label, run):
    plan, change = run["plan"], run["change"]
    lines = [
        f"## Plan {label}", "", "### Circuit check", "",
        "| Circuit | Type | As drawn | Required | Complies | Issue |",
        "|---|---|---|---|---|---|",
    ]
    for c in plan["circuits"]:
        drawn = f"{c['mcb_rating_a_as_drawn']:g} A, {c['cable_mm2_as_drawn']:g} mm², " \
                f"{_rcd(c['rcd_protected_as_drawn'], 'RCD', 'no RCD')}"
        required = f"{c['required_mcb_rating_a']:g} A, {c['required_cable_mm2']:g} mm², " \
                   f"{_rcd(c['rcd_required'], 'RCD', 'no RCD')}"
        lines.append(f"| {c['id']} | {c['circuit_type']} | {drawn} | {required} | "
                     f"{_rcd(c['compliant'], 'yes', 'no')} | {c['issue'] or ''} |")
    lines += ["", "### Sequence of work", ""]
    for s in sorted(plan["sequence"], key=lambda s: s["step"]):
        test = f": {s['test']}" if s["test"] else ""
        lines.append(f"- Step {s['step']} ({s['kind']}{test}). {s['action']}")
    lines += [
        "", "### Response to the change notice", "",
        f"{change['id']}, {change['circuit_type']}: {change['required_mcb_rating_a']:g} A MCB, "
        f"{change['required_cable_mm2']:g} mm² cable, {_rcd(change['rcd_required'], 'RCD required', 'no RCD')}. "
        f"Tests: {', '.join(change['tests'])}.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("task_id")
    parser.add_argument("--samples", nargs="+", type=int, default=[1])
    parser.add_argument("--raters", nargs="+", default=["R1", "R2", "R3"])
    args = parser.parse_args()

    task_dir = REPO_ROOT / "tasks" / args.task_id
    task = yaml.safe_load((task_dir / "task.yaml").read_text(encoding="utf-8"))
    scheme = yaml.safe_load((task_dir / "marking_scheme.yaml").read_text(encoding="utf-8"))
    judged = [a for a in scheme["aspects"] if a["type"] == "judgement"]
    runs = sorted(p for n in args.samples for p in (REPO_ROOT / "runs" / args.task_id).glob(f"*__s{n}.json"))
    random.shuffle(runs)
    key = {label: path.stem for label, path in zip(ascii_uppercase, runs)}

    out_dir = REPO_ROOT / "ratings" / args.task_id
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(task_dir / task["assets"]["diagram"], out_dir / "diagram.png")

    brief, change_notice = ((task_dir / name).read_text(encoding="utf-8") for name in task["turns"])
    lines = [
        f"# Rating packet: {args.task_id}, {task['task_name']}", "",
        f"You will rate {len(key)} plans written for the same task. Rate each plan on each aspect below, on "
        "the WorldSkills 0 to 3 judgement scale, independently and without conferring. Record your "
        "scores in the table at the end of this packet.", "",
        "The automatically measured aspects (circuit values, flagged non-compliances, test order, and "
        "the change notice values) are scored separately and are not part of this rating.", "",
        "## Task given to the agent", "", brief.strip().replace("\n## ", "\n### "), "",
        "![Design drawing](diagram.png)", "",
        "Second turn, issued after the plan:", "", f"> {change_notice.strip()}", "",
        "## Notes for raters", "", scheme["rater_notes"].strip(), "",
        "## Aspects to rate", "",
    ]
    for a in judged:
        lines += [f"**{a['id']}** ({a['marks']} marks). {a['question']}", ""]
        lines += [f"- {score}: {text}" for score, text in a["benchmarks"].items()] + [""]
    lines += [render_plan(label, json.loads(path.read_text(encoding="utf-8"))) for label, path in zip(key, runs)]
    lines += [
        "## Your scores", "", "Rater code: ______", "",
        f"| Plan | {' | '.join(a['id'] for a in judged)} | Comment |",
        f"|---|{'---|' * len(judged)}---|",
        *(f"| {label} |{'  |' * len(judged)}  |" for label in key), "",
    ]
    packet = "\n".join(lines)
    (out_dir / "packet.md").write_text(packet, encoding="utf-8")
    image = base64.b64encode((out_dir / "diagram.png").read_bytes()).decode()
    body = markdown.markdown(packet.replace("(diagram.png)", f"(data:image/png;base64,{image})"), extensions=["tables"])
    (out_dir / "packet.html").write_text(
        f"<!doctype html><html><head><meta charset='utf-8'><title>Rating packet {args.task_id}</title>"
        f"<style>{STYLE}</style></head><body>{body}</body></html>", encoding="utf-8")

    with open(out_dir / "ratings.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["plan", "aspect", "rater", "score", "comment"])
        writer.writerows([label, a["id"], rater, "", ""] for rater in args.raters for label in key for a in judged)
    (out_dir / "key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    print(f"wrote packet for plans {', '.join(key)} to {out_dir.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
