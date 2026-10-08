# Phase 0A — Setup sandbox, ownership and access

Added at the user's request on 2026-10-08. Status: pending. This phase follows Phase 0 planning and precedes Phase 1 runtime/prototype work. External account setup is separate from deployment of this application; cloud deployment remains Phase 9.

## Phase 0A.1 — Create the Atlassian account

User confirmed no Atlassian account exists yet. Choose a user-owned email, register the account, complete email verification and verify login. The user enters credentials and verification codes privately. Record only completion status/date. Account creation is pending; no signup has been performed. See the detailed checklist in ../../PHASES.md.

## Phase 0A.2 — Setup sequence and evidence

1. Assign a named business decision owner and credential custodian. Confirm V1 synthetic policies and allowed actions. Do not assume William holds these roles without confirmation.
2. Select Jira product/edition and create or designate an isolated test project/site. Use synthetic tickets and two tenant mappings. Record site/project IDs and product edition in local configuration; no customer tickets. Proposed adapter: Jira Cloud platform REST API v3. If Service Management request/approval APIs are needed, document that API separately before implementation.
3. Configure an integration identity with only required read/link/comment/transition permissions. Store credentials in environment/secret storage outside Git. Record credential reference, expiry and custodian, never the value. Verify permitted read, denied out-of-scope access and a reversible synthetic write/read-back with the setup utility; this does not replace Phase 5 end-to-end acceptance.
4. Select access-management and service-health sandbox targets. Phase 1 uses an independent fake target ledger; real connected targets must support authoritative read-back. If actual targets are unavailable, record Phase 5 as blocked with the missing account/permission and next action. Do not label a Jira update as proof of external access or service recovery.
5. Prepare Docker Desktop Linux/WSL and verify engine/Compose readiness without starting the old stack. Pin exact runtime/image versions and resource limits. New application services and n8n installation remain Phase 1. No local load/stress tests on this laptop.
6. Select n8n version and review the intended usage against its license. Record exact tag/digest after registry verification; do not use a moving `latest` tag for comparisons. Resolve PostgreSQL/pgvector version and lockfile compatibility before install.
7. Record provider account availability and local inference plan. Hosted-provider canaries remain Phase 3. Select Ollama/model version, quantization and license after memory compatibility review; no model download or inference is needed to unblock the deterministic Phase 1 prototype.

## Observed environment

- CPU: Intel Core i7-13620H, 10 cores / 16 logical processors.
- Physical RAM: 16,868,962,304 bytes (about 15.7 GiB).
- GPU: NVIDIA GeForce RTX 4050 Laptop GPU; `nvidia-smi` reports 6141 MiB and driver 610.78. Use this reading, not the truncated WMI AdapterRAM field.
- Baseline Python 3.12.13; Node 22.19.0; pnpm 10.21.0. These are observed versions, not a freshly resolved new-project lock.
- WSL lists Ubuntu, docker-desktop and podman-machine-default. Docker Linux API pipe was unavailable during the read-only check. No services were started.
- No matching Docker/Ollama/Celery processes were returned by the limited process-name query. This does not prove there are no WSL or remote jobs. Old runtime queues remain unqueried; the new prototype must stay isolated.

## Exit gate

Owner/custodian named; Jira edition/project and access checked or explicitly deferred with a blocker; target contracts selected; Linux runtime readiness and version pins recorded; secret-storage references established; synthetic boundaries agreed. Any deferred external target blocks its connected acceptance, not creation of contract fixtures. Required local runtime readiness must pass before Phase 1 services start.

Output: `setup-readiness.md` with item, status, owner, evidence path, next action and affected phase. Leave unchecked items visible; no setup is claimed by writing this plan.

## Official references checked for planning

- [Jira Cloud REST API v3](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro): chosen API family, pending actual tenant/product verification.
- [n8n Docker Compose installation](https://docs.n8n.io/deploy/host-n8n/install-options/install-using-docker-compose.md): follow current Compose instructions during setup. The older Docker page flags itself outdated, so its listed release is not used as a project pin.
- [n8n license](https://docs.n8n.io/sustainable-use-license): review for the selected deployment/use model.
- [Ollama hardware support](https://docs.ollama.com/gpu): compatibility reference; installed driver alone does not prove a selected model fits memory.
