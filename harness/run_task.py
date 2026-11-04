"""Run a task against a model under one or more reasoning-effort settings.

Usage:
    python -m harness.run_task CON-01 gpt-5.6-luna --efforts low medium high --samples 3
"""

import argparse
import base64
import hashlib
import json
from datetime import datetime, timezone
from importlib.metadata import version

import yaml

from harness.models import REPO_ROOT, client_for


def _schema_format(name, schema):
    return {"format": {"type": "json_schema", "name": name, "schema": schema, "strict": True}}


def _usage(response):
    usage = response.usage
    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "reasoning_tokens": usage.output_tokens_details.reasoning_tokens,
    }


def _task_digest(task_dir, task):
    digest = hashlib.sha256()
    for name in [*task["turns"], task["assets"]["diagram"], task["output_schema"]]:
        digest.update((task_dir / name).read_bytes())
    return digest.hexdigest()


def run_once(client, deployment, task_dir, task, effort):
    schemas = json.loads((task_dir / task["output_schema"]).read_text(encoding="utf-8"))
    brief, change_notice = (
        (task_dir / name).read_text(encoding="utf-8") for name in task["turns"]
    )
    image = base64.b64encode((task_dir / task["assets"]["diagram"]).read_bytes()).decode()

    plan = client.responses.create(
        model=deployment,
        reasoning={"effort": effort},
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": brief},
                {"type": "input_image", "image_url": f"data:image/png;base64,{image}"},
            ],
        }],
        text=_schema_format("plan", schemas["plan"]),
    )
    change = client.responses.create(
        model=deployment,
        reasoning={"effort": effort},
        previous_response_id=plan.id,
        input=change_notice,
        text=_schema_format("change", schemas["change"]),
    )
    return {
        "served_model": plan.model,
        "plan": json.loads(plan.output_text),
        "change": json.loads(change.output_text),
        "usage": {"plan": _usage(plan), "change": _usage(change)},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("task_id")
    parser.add_argument("model_id")
    parser.add_argument("--efforts", nargs="+", default=["medium"])
    parser.add_argument("--samples", type=int, default=1)
    args = parser.parse_args()

    task_dir = REPO_ROOT / "tasks" / args.task_id
    task = yaml.safe_load((task_dir / "task.yaml").read_text(encoding="utf-8"))
    out_dir = REPO_ROOT / "runs" / args.task_id
    out_dir.mkdir(parents=True, exist_ok=True)
    client, deployment = client_for(args.model_id)

    for effort in args.efforts:
        for sample in range(1, args.samples + 1):
            result = run_once(client, deployment, task_dir, task, effort)
            record = {
                "task_id": args.task_id,
                "model_id": args.model_id,
                "deployment": deployment,
                "reasoning_effort": effort,
                "sample": sample,
                "preparation_regime": "zero-shot",
                "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "openai_sdk": version("openai"),
                "task_sha256": _task_digest(task_dir, task),
                **result,
            }
            path = out_dir / f"{args.model_id}__{effort}__s{sample}.json"
            path.write_text(json.dumps(record, indent=2), encoding="utf-8", newline="\n")
            print(f"wrote {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
