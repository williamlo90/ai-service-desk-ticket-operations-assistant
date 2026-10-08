# Local evidence extraction runbook

## Experimental candidate and provenance

Ollama is not quality-accepted for the lab release. William explicitly deferred
its improvement while accepting the OpenAI profile; see `accepted-scope.json`.
The latest report records the local shortcomings. Recovery steps below describe
the runner: the reload probe runs only after quality passes, so a failed run does
not establish reload recovery. Final unload is still attempted and recorded.

Qwen3 4B Instruct, Q4_K_M, through Ollama's loopback API on
`127.0.0.1:11434`. The [official model entry](https://ollama.com/library/qwen3:4b-instruct)
lists a roughly 2.5GB artifact and Apache-2.0 license. The acceptance runner checks
the expected registry digest prefix, records the full digest and returned license
hash, and freezes the full digest before inference. A moving tag alone is not a pin.
The local prompt adds omission examples. Code requires non-empty supporting quotes
and conservatively omits explicit absence statements and ticket fields without an ID,
retaining discarded evidence for inspection. This bounded guard is not a general
semantic verifier. Fact quotes are selected from authorized full texts/sentence
spans, preserving exact source context rather than claiming a generated factual
summary. Quoted instructions remain untrusted data. Local v4 uses development regression cases and a 16-case holdout
that earlier local versions never attempted.
See `local-evidence-v4.json` and `evals/phase6-local-v4/local-freeze.json` for
the actual result. Hardware is recorded separately in `local-hardware.json`.

This task reuses the existing portable Ollama service (0.40.1), originally started
from the Odoo project's local runtime directory. No Odoo source, configuration,
container, model or process was replaced/stopped. Its model cache is shared; the
new model download adds disk usage. Inference runs sequentially with one selected
model, then that model is unloaded. This is not an isolated performance environment.

## Provision and verify

The initial `/api/pull` request for `qwen3:4b-instruct` needs internet and about
2.5GB of download/storage. Ollama verifies downloaded blobs. After provisioning,
`/api/tags` supplies the manifest digest and `/api/show` supplies metadata/license.
The model's tokenizer/weights are contained in the GGUF artifact; its manifest
also includes the prompt template and parameters. Keep the recorded digest with
the deployment, not merely the tag. No separate embedding model is used: retrieval
is bounded lexical selection over explicit authorized sources.

The acceptance script is `python scripts/check_local_evidence_v4.py`. It refuses to
overwrite an existing report/freeze. For another evaluation, create a new versioned
run/holdout rather than deleting evidence or blindly retrying. Offline verification
is `python scripts/check_phase6_gate.py`; this makes no model or hosted calls.

Settings: context 4,096; maximum generated tokens 1,000; temperature 0; seed 42;
2 CPU threads; requested GPU layers 99; thinking disabled; concurrency one;
60-second request timeout; two-minute keep-alive between requests. Actual GPU
offload is checked through `/api/ps`, rather than inferred from hardware presence.
[Ollama's thinking API](https://docs.ollama.com/capabilities/thinking) documents the
`think` flag. The instruct profile returns schema-constrained evidence without a
separate reasoning transcript.

## Readiness, failure and cleanup

The runner checks the model digest, warms up on a development case, evaluates the
development split, and proceeds to held-out cases only when development passes.
Generated field quotes are validated against authorized sources. Unknown fields,
duplicate fields, malformed JSON and ungrounded quotes fail closed. Failed calls
stay in the case denominator. No automatic hosted fallback or request retry exists.

After evaluation, an empty `/api/generate` request with `keep_alive: 0` unloads
only the selected model. A development probe loads it again to test recovery;
the final cleanup unloads it and checks `/api/ps`. The daemon and other services
remain running. The downloaded artifact remains cached for later use.

Timeout bounds the HTTP call, not guaranteed immediate cancellation of inference.
If a timeout occurs, inspect the loopback runtime and wait for its keep-alive to
expire; do not kill a shared service or assume the request never ran. This pipeline
is advisory and has no action tools or credentials. For runtime-unavailable cases,
return an error for operator review. OOM, daemon crash, host reboot, sustained load
and recovery under concurrent external workloads belong to Phase 7 hardening;
model unload/reload does not prove those behaviors.

## Upgrade, rollback and retention

An upgrade uses a separate tag/digest and a fresh frozen evaluation before adoption.
Retain the previous model until the new one passes. Rollback selects the previously
recorded digest/configuration and repeats the relevant canary; never silently switch
providers in an action workflow. Unload inactive models before reclaiming GPU memory.
Delete only a specifically retired model through Ollama's model-management API;
do not remove a shared cache directory. No automatic cleanup or update job is installed.

Inputs here are synthetic. The application stores sanitized outputs and metadata;
local model/runtime storage is not an audited retention guarantee. Review runtime
logs and local file policy before using sensitive data. Inference uses a fixed
loopback endpoint and no provider keys, but the complete Jira-based product still
depends on SaaS connectivity. Local inference does not make the entire system offline.
