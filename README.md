# AI Service Desk & Ticket Operations Assistant

Proyek 01: **AI Service Desk & Ticket Operations Assistant**

Tanggal rencana: 2026-10-08. Status: **Phase 1A core backend tersedia; Phase 1B runtime sedang dikerjakan bertahap**. Checklist hanya dicentang setelah artefak dan verifikasinya tersedia.

**Pengguna:** Service desk lead dan support specialist.

**Hasil bisnis:** Mengubah tiket masuk menjadi pekerjaan yang jelas, tindakan yang disetujui, dan hasil penyelesaian yang terverifikasi.

**Alur:** Tiket Jira masuk → klasifikasi dan pengumpulan konteks → retrieval SOP → rencana tindakan → approval sesuai risiko → update/action → periksa hasil di sistem tujuan → tutup atau eskalasi → laporan.

**Stack keputusan:** Python + FastAPI; TypeScript + React; custom MCP server TypeScript; LangGraph untuk workflow yang perlu checkpoint; PostgreSQL + pgvector; Docker Compose di Linux; Jira REST API; provider adapter OpenAI, Claude, Grok; Ollama.

**Automation:** Pakai n8n untuk integrasi workflow; evaluasi perluasan ownership lewat prototype. Lihat [N8N-AUTOMATION.md](N8N-AUTOMATION.md).

Pilihan framework adalah keputusan implementasi kita, bukan klaim bahwa JD mewajibkan merek framework tersebut. Versi API/library/model ditetapkan saat Phase 0 berdasarkan dokumentasi resmi dan lingkungan yang tersedia.

## Baseline dan reuse

Perluasan Case Resolution Copilot. Sumber: C:/Users/William/OneDrive/Dokumen/Agentic Project/case-resolution-copilot-rebuild. HEAD 1a88dbb; ada perubahan lokal production-validation yang belum di-commit pada pemeriksaan 8 Oktober. Approval snapshots, policy retrieval, audit, permissions, action gateway, idempotency, dan reconciliation sudah memiliki fondasi. Verifikasi ulang sebelum dipakai. Gap audit sebelumnya: intake masih menerima kategori dari pemanggil; receipt tindakan dan final outcome belum dibedakan cukup tegas; closure/reopen perlu diperkuat. Pertahankan domain sengketa tagihan/refund sebagai regression pack; tambahkan kasus service desk MSP yang spesifik. Jangan mengasumsikan perubahan lokal telah lulus hanya dari status Git.

## Dokumen kerja

- [PHASES.md](PHASES.md)
- [AI-AGENTS.md](AI-AGENTS.md)
- [REUSABLE-SKILLS.md](REUSABLE-SKILLS.md)
- [MCP-INTEGRATIONS.md](MCP-INTEGRATIONS.md)
- [BUSINESS-PLATFORM.md](BUSINESS-PLATFORM.md)
- [LOCAL-AI-AND-PROVIDERS.md](LOCAL-AI-AND-PROVIDERS.md)
- [SECURITY-TESTING-MONITORING.md](SECURITY-TESTING-MONITORING.md)
- [PROJECT-DELIVERY.md](PROJECT-DELIVERY.md)

## Ukuran keberhasilan

triage accuracy per kategori; policy-correct decision rate; verified resolution rate; false closure rate; auto-resolution coverage dari seluruh kasus; manual touches; reopen rate; p95 sampai hasil terverifikasi; biaya per kasus benar.

## Cara mulai

Progress 2026-10-08: inventaris awal Phase 0 tersedia di [Baseline inventory](docs/phase-0/BASELINE-INVENTORY.md), dengan [scope/dependency register](docs/phase-0/scope-and-dependencies.md) dan [source fingerprints](docs/phase-0/source-inventory.json). Pemeriksaan terbatas: 13 unit test baseline lulus. Kontrak pembanding v1, 14 reference fixtures, dan snapshot source lokal sudah tersedia. Lihat [kontrak](docs/architecture/comparison-contract.md) dan [manifest](docs/phase-0/artifact-manifest.json). Setup owner/sandbox/akses/runtime kini masuk [Phase 0A](docs/phase-0/SETUP-PHASE-0A.md) sebelum Phase 1; belum ada benchmark atau connected acceptance.

1. Buka PHASES.md dan kerjakan Phase 0.
2. Catat apa yang existing, perlu verifikasi, dan baru. Semua checklist folder ini dimulai belum selesai.
3. Buat satu alur lengkap, uji hasilnya, baru tambah variasi; ikuti urutan fase dan dependency.
4. Catat evidence path/run ID saat menutup fase. Cloud hanya pada Phase 9.

Folder ini berisi rencana, kontrak, skrip diagnostik, core backend Python dan runtime lokal PostgreSQL/n8n. Core dan API WSGI in-process memiliki 39 tests tanpa container; runtime sebelumnya lulus smoke checks. User sudah membuat akun owner n8n dan workflow sintetis. Kode API dengan penyimpanan memori tersedia; deployment API, SQL adapter, MCP dan workflow bisnis terhubung masih pending. Lihat [status Phase 1](docs/phase-1/STATUS.md), [panduan backend](backend/README.md) dan [panduan runtime](deploy/README.md).

## Keputusan kode existing

Kode lama boleh dipakai ulang, diganti atau dihapus berdasarkan hasil [ARCHITECTURE-COMPARISON.md](ARCHITECTURE-COMPARISON.md). Tidak ada kewajiban mempertahankan arsitektur hanya karena sudah dibangun. Implementasi baru dimulai dari core backend terisolasi; belum ada kode baseline yang dihapus.


Akun Atlassian dan Jira IT-1 sudah tersedia; diagnostic read berhasil. Sisa setup identity/owner dan akses tercatat di [PHASES.md](PHASES.md). Runtime lokal terisolasi memiliki panduan di [deploy/README.md](deploy/README.md).
