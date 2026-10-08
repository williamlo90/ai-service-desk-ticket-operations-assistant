# Automation Decision — 01 - AI Service Desk & Ticket Operations Assistant

> Current architecture decision: code-led V1 with outbound Jira polling.
> [ADR 003](docs/architecture/ADR-003-selected-code-led.md) supersedes earlier
> mandatory n8n ownership assumptions below. Existing n8n workflows are retained.

Status: **rencana; belum menjadi hasil benchmark atau implementasi baru**.

**Keputusan:** Pakai n8n untuk integrasi workflow; evaluasi perluasan ownership lewat prototype.

**Peran:** Tiket masuk, pengambilan konteks lintas aplikasi, routing, pengingat SLA, dan reporting. Domain service menjaga permissions, case state, approved actions, outcome verification dan reopen.

**Alasan:** Hybrid sebagai hipotesis awal. Bandingkan orchestration Python existing dengan n8n-led pada satu alur kasus utuh; orchestration lama boleh dihapus jika kandidat menang.

Dokumen ini menggantikan kewajiban lama memasang n8n di semua proyek. Lihat [keputusan portfolio](../AUTOMATION-DECISIONS.md).

## Workflow target

1. Tiket Jira masuk/berubah → triage dan context gathering → policy-grounded proposal → approval sesuai risiko → action → downstream outcome check → closure atau eskalasi. n8n dapat mengatur rangkaian dan handoff; pemilik state final diputuskan pada architecture comparison.
2. Jadwal → backlog/SLA query → authorized notification dan laporan; replay tidak membuat reminder atau action ganda.

## Ownership dan acceptance

- Pilih pemilik orchestration, retries, approval records dan business state secara eksplisit. Satu operasi bisnis punya satu sumber status otoritatif.
- n8n boleh menjalankan agent, tool calls, branching, wait/approval dan reusable sub-workflows bila cocok. Pembagian Python/n8n adalah keputusan proyek, bukan batas kemampuan n8n.
- Approval dari UI aplikasi maupun workflow harus terikat actor, tenant, payload/version dan kewenangan; penerimaan callback atau teks approved tidak cukup.
- Side effects membutuhkan deduplication/idempotency dan verifikasi hasil. Unknown outcomes direkonsiliasi sebelum retry; state berhasil di engine tidak otomatis berarti masalah bisnis selesai.
- Scope authorization berlaku pada semua jalur: assistant, MCP, worker, automation engine dan direct API.

## Checklist implementasi

- [ ] Tetapkan boundary n8n/domain service dan source of truth sebelum implementasi; gunakan architecture comparison bila memperluas repo existing.
- [ ] Siapkan n8n self-hosted lokal, service identity, encrypted credential storage, health, persistent state dan node/version compatibility.
- [ ] Implementasikan workflow target dan simpan export tersanitasi di `automation/n8n/`; credentials tidak masuk Git.
- [ ] Uji trigger → hasil platform, duplicate/out-of-order events, restart, expired token, wrong tenant, stale approval, timeout sesudah side effect, unknown outcome, dan safe replay.
- [ ] Catat outcome correctness, verified completion, p95 end-to-end, backlog, resources dan biaya; bukan node latency saja.
- [ ] Buktikan alert delivery, sanitized execution history/retention, restore dan import pada instance bersih.
- [ ] Sertakan owner, activation/deactivation, schedule/timezone, troubleshooting, dan rollback dalam delivery.

## Fase

Phase 0 menentukan ownership; Phase 1 menyiapkan runtime lokal; Phase 5 membangun connected workflows; Phase 7 menguji reliability; Phase 8 menyerahkan export/panduan; Phase 9 melakukan deployment cloud TERAKHIR dan runtime acceptance.


## Migrasi dari kode existing

Ikuti [ARCHITECTURE-COMPARISON.md](ARCHITECTURE-COMPARISON.md). Reuse bukan kewajiban; penggantian atau penghapusan kode diperbolehkan setelah replacement dibuktikan.
