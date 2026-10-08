# Custom MCP Server, APIs & Database

Proyek 01: **AI Service Desk & Ticket Operations Assistant**

Tanggal rencana: 2026-10-08. Status: **rencana implementasi; belum ada implementasi baru dalam folder ini**. Checklist hanya dicentang setelah artefak dan verifikasinya tersedia.

## Arsitektur keputusan

Assistant/client → **custom MCP server TypeScript** → domain API **Python** → **PostgreSQL** dan adapter **Jira**. MCP server tidak melewati business validation dengan menulis tabel langsung. AI memperoleh data SQL melalui query service yang terotorisasi dan terparameterisasi.

MCP server proyek ini punya capability spesifik, bukan server generik yang mengekspos semua API. Jika memakai konektor 02/03, import atau panggil kontraknya; jangan menyalin codebase konektor.

## Tools rencana

| Tool | Jenis | Kontrak ringkas |
| --- | --- | --- |
| `ticket.search` | read | query + scope → tiket yang boleh dibaca |
| `ticket.get_context` | read | ticket ID → fakta, riwayat, SOP |
| `ticket.propose_update` | prepare | ticket ID + expected version → proposal |
| `ticket.apply_approved_update` | write | proposal ID + approval ID + idempotency key → receipt |
| `ticket.verify_outcome` | read | action ID → hasil yang diverifikasi |
| `ticket.reopen` | write | case ID + evidence + approved reason → status baru |

## Syarat kontrak

- [ ] Pin MCP SDK dan protocol version yang didukung client; gunakan stdio untuk client lokal bila sesuai, authenticated HTTP untuk remote hanya saat deployment terakhir.
- [ ] Setiap tool memiliki description, strict input/output schema, source references, stable error codes, pagination bila perlu, dan output limits.
- [ ] Server memverifikasi identity, tenant/record scope, role, approval payload/version, serta idempotency key; input model bukan otorisasi.
- [ ] Write tools membutuhkan proposal dan approval sesuai risiko. Approval tidak boleh dibuat oleh agent yang hendak melakukan action tersebut.
- [ ] Uji protocol dari client, schema rejection, credentials expiry, injection, cancellation, error propagation, concurrency, dan retry.
- [ ] Simpan correlation ID dari assistant → MCP → Python → platform; logs cukup untuk diagnosis tanpa body sensitif secara default.

## Model data awal

tenant, case, external_ticket, message, policy_version, evidence, decision_brief, approval_snapshot, action_attempt, outcome_check, audit_event.

Tambahkan tenant foreign keys, unique constraints untuk external references/idempotency, optimistic versioning atau locking sesuai transaksi, migrations, retention, dan audit. SQL read-only query untuk reporting tidak menerima arbitrary SQL dari model.

**Selesai ketika:** satu alur melalui MCP mengubah atau membaca platform sesuai scope, database mencatat provenance, dan hasil benar dibuktikan lewat read-back/expected state. Unit tests langsung ke fungsi belum cukup untuk protocol acceptance.

## Hubungan dengan automation engine

Pakai n8n untuk integrasi workflow; evaluasi perluasan ownership lewat prototype. Agent dapat memakai custom MCP tools; workflow memakai API atau MCP sesuai kebutuhan. Semua jalur menuju kontrol domain otoritatif, tanpa dua implementasi business rules.
