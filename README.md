# PHYS-SKILL Benchmark (PSB)

Evaluation harness and task specifications for the PHYS-SKILL Benchmark, a skill-centric
framework for assessing embodied AI systems on occupational tasks, organized around vocational
skill competitions such as WorldSkills.

This repository accompanies the paper *A Reflection on Evaluating Embodied Skill in AI Systems*
(Maaradji, Djedidi, Maamar). The paper sets out the argument and the design; this repository
holds the instrument.

## Status

Early. The scoring rubric is defined. The first illustrative task and its evaluation are in
progress.

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

## Layout

- `config.yaml`: models under evaluation, and where their credentials come from
- `rubric/dimensions.yaml`: the eight scoring dimensions and their weights
- `harness/`: model access and evaluation scripts

## License

Code is released under the Apache License 2.0 (see `LICENSE`). Task specifications, rubrics, and
results are released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
