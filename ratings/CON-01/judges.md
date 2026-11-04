# Judgement ratings for CON-01

The judgement aspects (TC-J1, PL-J1, EF-J1) of all nine runs were rated on 3 October 2026 by three
AI judges, each a different large language model, standing in for the three human experts that
WorldSkills practice calls for. The judges come from a different developer than the evaluated
model, so no model judged its own output.

| Rater | Model |
|---|---|
| J1 | claude-fable-5-1 |
| J2 | claude-opus-5-5 |
| J3 | claude-sonnet-5-5 |

Each judge ran in its own context and read only the blind packet (`packet.md`, plans labelled A to
I) and the drawing, as the session logs show. None read the measurement results or `key.json`. The
restriction was an instruction in the prompt, not a technical limit. Each session also loaded the
project's instruction files, which describe the paper and name the evaluated model but contain no
results. Raw responses are in `judges/`; scores and reasons are transcribed to `ratings.csv`.

AI judges are not qualified electricians, and models trained by similar methods may agree more
than independent human experts would. These ratings illustrate the marking procedure; they do
not certify competence.

## Prompt

Identical for all three judges. `{packet}` and `{drawing}` were absolute paths to copies of
`packet.md` and `diagram.png` held outside this repository.

```
You are one of three independent judges marking a WorldSkills-style test project in the
Electrical Installations skill. Judge as an experienced electrical installation expert would.
Nine plans, labelled A to I, were written for the same task. Score each plan on three judgement
aspects, on the WorldSkills 0 to 3 scale, against the written benchmarks.

Work alone. Read exactly two files and nothing else: the rating packet at {packet} and the
design drawing at {drawing}. Do not open, list, or search any other file or directory, and do
not use any other tool. The packet contains the task given to the agent, notes for raters, the
aspects with their benchmarks, and the nine plans.

Score every plan on its own merits against the benchmarks, not against the other plans, and do
not try to infer which system or setting produced it. Use the whole scale where it is warranted.
Ignore the packet's request to fill in a table. Instead, return only a JSON object, with no
other text, in exactly this form:

{"A": {"TC-J1": {"score": 0, "reason": "..."}, "PL-J1": {"score": 0, "reason": "..."},
"EF-J1": {"score": 0, "reason": "..."}}, "B": {...}, ..., "I": {...}}

Each score is an integer from 0 to 3. Each reason is one or two sentences naming the specific
features of the plan that determined the score.
```
