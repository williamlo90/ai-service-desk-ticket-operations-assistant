# Business Platform & Workflow Integration

> Current architecture decision: code-led V1 with outbound Jira polling.
> [ADR 003](docs/architecture/ADR-003-selected-code-led.md) supersedes earlier
> mandatory n8n ownership assumptions below. Existing n8n workflows are retained.

Proyek 01: **AI Service Desk & Ticket Operations Assistant**

Tanggal rencana: 2026-10-08. Status: **rencana implementasi; belum ada implementasi baru dalam folder ini**. Checklist hanya dicentang setelah artefak dan verifikasinya tersedia.

**Platform utama:** Jira.

**Alur bisnis:** Tiket Jira masuk → klasifikasi dan pengumpulan konteks → retrieval SOP → rencana tindakan → approval sesuai risiko → update/action → periksa hasil di sistem tujuan → tutup atau eskalasi → laporan.

## Checklist implementasi

- [ ] Tetapkan produk/edition/API version, permission scopes, batas sandbox, dan credential owner. Verifikasi endpoints dari dokumentasi resmi saat implementasi.
- [ ] Dokumentasikan entity mapping, external IDs, sumber otoritatif tiap field, timestamp/timezone, freshness, dan aturan konflik.
- [ ] Implementasikan read/sync terlebih dahulu, kemudian prepare/approve/write/verify. Webhooks perlu autentikasi/signature bila tersedia dan replay protection.
- [ ] Gunakan test tenant atau instalasi lokal; data sintetis mengandung kasus valid, ambiguity, dan exception.
- [ ] Tangani pagination, rate limit, retries dengan backoff, expired credentials, deleted records, event out-of-order, dan partial success.
- [ ] Catat result verification yang spesifik terhadap operasi. HTTP 2xx/accepted tidak otomatis berarti hasil bisnis final.
- [ ] Terapkan keputusan automation: Pakai n8n untuk integrasi workflow; evaluasi perluasan ownership lewat prototype. Rincian di [N8N-AUTOMATION.md](N8N-AUTOMATION.md); semua jalur memakai aturan akses dan verifikasi hasil yang konsisten.
- [ ] Buktikan mapping/business configuration kedua, recovery unknown outcome, serta tidak adanya duplicate side effects dalam skenario yang diuji.

## Akses yang belum tersedia

Catat dependency nyata beserta status dan langkah memperoleh akses. ConnectWise/Microsoft 365/Odoo hosted mungkin membutuhkan tenant, scope, edition, atau lisensi yang sesuai. Jangan menganggap sandbox gratis tersedia. Sambil menunggu, lanjutkan contract fake dan lokal, tetapi connected acceptance tetap pending. Tidak ada permintaan agar orang lain mencoba demo sebagai prerequisite.

## Bukti yang disimpan

- Request/response disanitasi atau snapshot field penting; bukan credentials atau data pelanggan.
- External record ID, approval ID, source versions, timestamp, expected outcome, observed outcome, dan read-back.
- Hasil retry/concurrency dan bukti jumlah side effects di platform tujuan.
- Batas integrasi yang masih draft-only, sandbox-only, atau belum diuji live ditulis jelas.

**Selesai ketika:** business owner bisa mengikuti satu pekerjaan dari input sampai hasil platform, termasuk satu kegagalan dan pemulihannya.
