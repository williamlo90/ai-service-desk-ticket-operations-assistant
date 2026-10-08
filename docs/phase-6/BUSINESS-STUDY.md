# Manual versus assisted pilot protocol

Status: eight-task diagnostic pilot completed by William;
see [results](BUSINESS-RESULTS.md). Because current model quality
has not passed, this is a correction/usability diagnostic using cached advice,
not the post-acceptance productivity study described below.

William is the lab reviewer; no synthetic timing is presented
as human effort, savings or ROI. Provider latency alone is not operator productivity.

Use a new matched set of synthetic tickets after technical quality acceptance.
For each category choose two comparable cases with the same information burden;
alternate manual-first and assisted-first order to reduce learning effects. Do not
give the same person the answer key or an identical ticket before the timed task.
Capture participant, case, condition, order and UTC start/end times locally.

Task: identify category, relevant evidence, missing details and safe next step.
Both conditions use the same SOP, role and completion rubric. Manual means no model
output. Assisted means the model proposes facts and the human reviews/corrects them.
Do not execute real entitlements or Jira writes during this study.

Record active reading/editing seconds, provider waiting seconds, interruption
seconds, correction count and total elapsed seconds separately. Do not double-count
overlapping waiting and active work. A reviewer grades both submissions against the
same reference, including authorization and no unsupported success claim.

Compare time only for equivalently correct submissions; disclose excluded failures,
sample sizes, correctness and correction rates alongside time. Report paired
differences and raw observations. A single-operator lab pilot is not a population
ROI estimate. If no human session occurs, the gate remains pending.

Suggested CSV columns:
`participant,case_id,pair_id,condition,order,started_utc,ended_utc,active_seconds,waiting_seconds,interruption_seconds,elapsed_seconds,corrections,correct,reviewer`
