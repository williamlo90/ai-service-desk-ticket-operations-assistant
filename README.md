# AI Service Desk & Ticket Operations Assistant

Proyek 01: **AI Service Desk & Ticket Operations Assistant**

Tanggal rencana: 2026-10-08. Status: **Phase 1-4 pra-Docker selesai; Phase 5 integrasi runtime belum dimulai**. Checklist hanya dicentang setelah artefak dan verifikasinya tersedia.

**Pengguna:** Service desk lead dan support specialist.

**Hasil bisnis:** Mengubah tiket masuk menjadi pekerjaan yang jelas, tindakan yang disetujui, dan hasil penyelesaian yang terverifikasi.

**Alur:** Tiket Jira masuk → klasifikasi dan pengumpulan konteks → retrieval SOP → rencana tindakan → approval sesuai risiko → update/action → periksa hasil di sistem tujuan → tutup atau eskalasi → laporan.

**Implementasi saat ini:** Python domain service dan WSGI intake, TypeScript MCP
server/reference client, adapter PostgreSQL/Jira, empat reusable skills, serta
adapter OpenAI/Claude/Grok/Ollama. Validasi menggunakan target dan transport sintetis.

**Target integrasi:** FastAPI/React, PostgreSQL + pgvector, runtime Docker lokal,
Jira dan model nyata. Ownership workflow code-led/n8n-led ditentukan lewat
perbandingan Phase 5; LangGraph digunakan bila keputusan checkpoint memerlukannya.
Lihat [rencana fase](PHASES.md) dan [handoff integrasi](docs/phase-5/HANDOFF.md).

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

1. Baca [catatan belajar per phase](docs/learning/README.md). Setiap phase punya
   satu commit sehingga perubahan bisa dipelajari secara bertahap.
2. Jalankan tes Python dari folder backend:
   `python -B -m unittest discover -s tests -v`.
3. Dari mcp-server, instal dependency terkunci dengan
   `npm ci --ignore-scripts --no-audit --no-fund`, lalu `npm test`.
4. Baca [handoff Phase 5](docs/phase-5/HANDOFF.md) sebelum integrasi runtime.

Hasil terakhir: **74 tes Python + 6 tes MCP lulus**. Tes menggunakan proses lokal,
identitas sintetis, memory store, DB-API spies dan fake transports; tidak memakai
Docker, .env, database nyata atau panggilan provider/Jira live. Instalasi npm
memerlukan registry. Tidak ada klaim benchmark AI, ROI atau connected acceptance.

[Kontrak pembanding](docs/architecture/comparison-contract.md) dan 14 reference
fixtures tetap menjadi gate integrasi tersendiri. [Setup readiness](docs/phase-0/setup-readiness.md)
mencatat prasyarat owner/identity/sandbox yang masih terbuka. Bukti runtime lama
tersedia sebagai snapshot historis; bukan validasi deployment saat ini.

## Keputusan kode existing

Kode lama boleh dipakai ulang, diganti atau dihapus berdasarkan hasil [ARCHITECTURE-COMPARISON.md](ARCHITECTURE-COMPARISON.md). Tidak ada kewajiban mempertahankan arsitektur hanya karena sudah dibangun. Implementasi baru dimulai dari core backend terisolasi; belum ada kode baseline yang dihapus.


Akun Atlassian dan Jira IT-1 sudah tersedia; diagnostic read berhasil. Sisa setup identity/owner dan akses tercatat di [PHASES.md](PHASES.md). Runtime lokal terisolasi memiliki panduan di [deploy/README.md](deploy/README.md).
