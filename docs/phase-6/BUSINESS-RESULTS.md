# Human correction pilot — completed

William completed all eight tasks on 2026-10-08, 23:06–23:12 WIB: four manual and
four assisted, across four matched category pairs. Raw answers/timing remain local
in `local/phase6/human-pilot.json`. `business-pilot-results.json` contains the
recomputed dimensions and source hash; answers and grading rules were not changed.

| Dimension | Manual | Assisted |
| --- | --- | --- |
| Correct category | 4/4 | 4/4 |
| Exact missing-field selection | 2/4 | 3/4 |
| Verbatim source quotation | 0/4 | 4/4 |
| Correct next step | 3/4 | 2/4 |
| All four rubric dimensions correct | 0/4 | 2/4 |
| Recorded active time, descriptive total | 220.053s | 151.245s |

**No matched pair has two fully correct submissions under the frozen rubric.**
Therefore this pilot does not support a correctness-matched efficiency improvement
or ROI claim. The time totals are observations, not a measured saving. No pauses
were recorded; 371.298s total active time depends on the participant using Pause
for any interruptions. Advice was cached, so provider waiting time was excluded.

## Findings for the product and training

- All category choices were correct. The main friction was not category recognition.
- Manual evidence was paraphrased or retyped. The exact-quote rule rejected it,
  including the out-of-scope case whose category, missing fields and next step were
  correct. Assisted evidence was prefilled. This introduces a UI/transcription
  advantage and prevents interpreting the difference as pure reasoning quality.
  A later pilot should offer the same source-selection/copy interaction in both
  conditions and separately evaluate faithful summarization if that is desired.
- The incident symptom `connection refused` was already present. Both submissions
  nevertheless marked symptoms as missing, including acceptance of the model's
  extra field. Only the service name needed clarification.
- A missing related-ticket identifier calls for clarification before preparing a
  relationship action. The manual answer routed out of scope; the assisted answer
  selected preparation for approval. Neither is the required next step yet.
- Category/missing-field selections were not changed from model suggestions in any
  assisted task. This metric covers two answer fields, not every click or edit.
  It indicates that this pilot did not demonstrate correction of the known faulty
  incident advice. It does not establish why the participant kept the defaults.

This is an engineering interpretation, not an independent human semantic sign-off.
The pilot is complete as a diagnostic exercise. It does not close model-quality,
business acceptance or production-readiness gates. Next work should improve the
clarification model and teach the distinction between clarification, preparation
for approval and out-of-scope routing before a fresh matched study.

Reproduce: `python scripts/analyze_business_pilot.py`. It reads the completed local
observations, validates identity/timing and recomputes grades without modifying raw
answers. No model call or business-system mutation is performed.
