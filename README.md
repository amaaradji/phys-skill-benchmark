# PHYS-SKILL Benchmark (PSB)

Evaluation harness and task specifications for the PHYS-SKILL Benchmark, a skill-centric
framework for assessing embodied AI systems on occupational tasks, organized around vocational
skill competitions such as WorldSkills.

This repository accompanies the paper *A Reflection on Evaluating Embodied Skill in AI Systems*
(Maaradji, Djedidi, Maamar). The paper sets out the argument and the design; this repository
holds the instrument.

## Status

Early. One task, CON-01 (electrical installation planning from a wiring diagram, modeled on
WorldSkills Electrical Installations), has been run against one model at three reasoning-effort
settings, three samples each. Its judgement aspects were rated by three AI judges, standing in
for human experts (`ratings/CON-01/judges.md`). Results are in `results/CON-01/summary.md`.

## Setup

Python 3.11.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Each model in `config.yaml` names the environment variables that hold its key, endpoint, and
deployment. Set them as user environment variables, or copy `.env.example` to `.env` and fill it
in. `.env` is git-ignored and must never be committed.

The endpoint may be either the Azure OpenAI v1 URL or an Azure AI Foundry project URL; the harness
derives the v1 URL from either.

## Check the connection

```
python -m harness.smoke_test
```

## Running a task

```
python -m harness.run_task CON-01 gpt-5.6-luna --efforts low medium high --samples 3
python -m harness.score CON-01
```

`run_task` writes one JSON record per run to `runs/<task>/`, with the model's outputs, token
usage, SDK version, timestamp, and a hash of the task files. `score` checks every measurement
aspect of the task's marking scheme, adds judgement marks once ratings exist, and writes
`results/<task>/scores.csv` and `summary.md`.

## Judgement ratings

Marking follows WorldSkills practice: measurement aspects score full marks or zero against a
stated criterion, and judgement aspects are scored by three judges on a 0 to 3 scale against
written benchmarks.

```
python -m harness.rater_packet CON-01 --samples 1 2 3
```

This writes a blind packet to `ratings/<task>/` (`packet.html` is self-contained), a rating sheet
`ratings.csv`, and `key.json`, which maps plan labels to runs. Keep the key from the raters until
they have rated; it is committed afterwards so that the scores can be reproduced. Labels are
reshuffled on every call, so do not regenerate a packet once it has been sent. Enter the panel's scores in `ratings.csv` and rerun `score`, which then reports the
renormalized totals and inter-rater agreement (Krippendorff's alpha, ordinal).

## Known issues

- The CON-01 brief requires all six verification tests for every circuit, including RCD operation
  on C3 to C5, which need no RCD under the specification. Four of the nine plans resolved the
  conflict with a step or sentence on RCD operation for those circuits. Judges counted this against
  conciseness, and on TC-J1 it may have cost the 41-step plan about two points of its total. The runs
  and ratings were produced with this wording and are unchanged, because the run records carry a hash of the task
  files. The next revision of the task should require each test only where it applies.
- `run_task` uses the Responses API, which reports only the deployment name, so the run records do
  not carry a model version. A Chat Completions call to the same deployment on 4 November 2026
  returned `gpt-5.6-luna-2026-07-09`.

## Layout

- `config.yaml`: models under evaluation, and where their credentials come from
- `rubric/dimensions.yaml`: the eight scoring dimensions and their weights
- `tasks/<task>/`: brief, change notice, drawing, output schema, and marking scheme
- `harness/`: model access, task runner, scorer, and rating packet builder
- `runs/`, `results/`, `ratings/`: raw outputs, scores, and panel ratings

## License

Code is released under the Apache License 2.0 (see `LICENSE`). Task specifications, rubrics, and
results are released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
