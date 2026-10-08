# Local runtime preparation — 2026-10-08

Docker Linux and Compose are installed and responsive. Runtime capacity remains a startup gate: the first host sample had about 1.2 GiB free while other project containers were active. Do not stop unrelated projects or change global WSL memory/CPU settings as part of this setup.

Read-only repeatable check: `powershell -NoProfile -File scripts/check_docker_readiness.ps1`. Evidence: `docker-readiness.json`. Exit 0 means the basic readiness checks pass, 2 means insufficient headroom/port conflict/non-Linux engine, 1 means inspection failed. No `.env` access. Free memory can change; rerun immediately before starting the prototype.

## Planned isolated Phase 1 configuration

| Component | Initial ceiling | Exposure / persistence |
| --- | --- | --- |
| PostgreSQL with pgvector | 512 MiB, 0.5 CPU | Optional loopback 127.0.0.1:5433; dedicated named volume |
| n8n editor/orchestrator | 1 GiB, 1 CPU | 127.0.0.1:5678; dedicated persistent n8n volume |
| FastAPI application, when implemented | 512 MiB, 0.5 CPU | Loopback port selected at implementation |

These are initial resource budgets, not tested sizing. On 2026-10-08 the user authorized staged startup below the original 4 GiB full-stack buffer. Use `-Mode database` (1 GiB host free, 512 MiB cap) or `-Mode n8n` (1 GiB host free AND 2 GiB Linux MemAvailable, 1 GiB cap), measure after each service, and stop expansion if resources are insufficient. Windows and Linux memory overlap and must not be added; Linux's reclaimable cache is considered for the second service. The default full-stack diagnostic retains its 4 GiB conservative guard. None of these values are vendor minimum requirements. Do not start model inference, frontend compilation, load tests or several candidate stacks simultaneously.

Use Compose project name `service-desk-lab`, a dedicated network and named volumes. The application and n8n must use separate database roles/databases. Do not share databases or queues with Odoo, ConnectWise or invoice projects. No privileged containers, Docker socket mounting, public tunnel or n8n AI Assistant sandbox is needed for the initial deterministic workflow. Jira credentials are not passed wholesale to every container.

## Version selection status

- Engine observed: 29.8.0; Docker Desktop 4.92.0; Compose 5.5.1; WSL2 Linux backend.
- Existing cached n8n `latest` resolves locally to version **1.104.2**. This cached tag is not proof of a current release and will not be used as the new-project pin.
- Existing pgvector `pg16` image is present, but application/migration compatibility and a current exact image pin still need verification.
- Installed runtime versions and exact image digests are recorded in `../phase-1/runtime-versions.json`; Compose uses immutable pins. These are verified lab versions, not a security-audit claim.
- Docker readiness does not close business ownership, permission-negative tests or connected action-target prerequisites.

Official setup reference: [n8n Compose guide](https://docs.n8n.io/deploy/host-n8n/install-options/install-using-docker-compose.md). That guide also includes optional n8n Assistant infrastructure; the proposed small prototype does not require that larger stack.

Runtime instructions now live in `../../deploy/README.md`. Stopping other active work still requires the user's selection.
