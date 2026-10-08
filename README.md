# AI Service Desk & Ticket Operations Assistant

Proyek 01: **AI Service Desk & Ticket Operations Assistant**

Tanggal rencana: 2026-10-08. Status: **Phase 1-4 pra-Docker selesai; Phase 5 berjalan: integrasi lokal MCP/API/PostgreSQL dan recovery sintetis lulus**. Checklist hanya dicentang setelah artefak dan verifikasinya tersedia.

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

## Progress integrasi lokal

Checkpoint Phase 5: **94 tes Python + 8 tes Node lulus**, ditambah 7 kelompok
uji PostgreSQL nyata dan 5 kelompok uji HTTP/MCP/recovery. Endpoint approval
supervisor terpisah dari MCP; state bertahan setelah restart proses, dan efek
target sintetis tidak digandakan setelah crash. Lihat
[status dan batas integrasi](docs/phase-5/HANDOFF.md).

William adalah business owner. Target live belum siap; integrasi memakai SQLite
sebagai target sintetis independen. Harness membersihkan database dan proses
uji sesudah selesai. Deployment pengguna, keputusan akhir code-led/n8n-led, serta
integrasi Jira/model live masih pending. Checkpoint Phase 5 disimpan dalam commit
atas instruksi William; gate akhir fase tetap terbuka.

Perbandingan reference worker sudah dijalankan: code-led dan n8n-led masing-masing
lulus **14/14 skenario dasar + 17/17 skenario policy v2**. Total 62 eksekusi skenario;
unit suite kini 94 Python tests. [ADR 001](docs/architecture/ADR-001-orchestration-checkpoint.md)
mempertahankan shared domain controls dan menunda pilihan engine sampai cakupan
scheduling serta effort pemeliharaan diuji setara. Ini belum menutup gate arsitektur.

Uji [native wait/restart](docs/phase-5/native-wait-comparison.json) juga lulus:
dua journey sintetis, masing-masing melewati dua restart engine saat menunggu
approval dan hasil target, lalu menutup kasus dengan satu efek target.
n8n melanjutkan execution ID yang sama.

[Pack recovery](docs/phase-5/recovery-comparison.json) lulus **7/7 skenario per
engine**: approval tidak valid, target lambat/gagal, response hilang, timeout
pembacaan, dan batas retry. Retry hanya membaca ulang hasil; tindakan tidak
dikirim ulang. Kasus yang perlu review tetap terbuka dengan escalation tersimpan.
Uji [crash saat backoff 70 detik](docs/phase-5/timer-comparison.json) juga lulus
untuk kedua engine. Sebanyak 47 tes regresi baseline lama lulus dari salinan
backup, dan rehearsal perubahan policy cukup menyentuh satu entri bersama pada
masing-masing kandidat. Crash timer pendek, transport retry, kesetaraan fitur
billing/refund dan effort operator masih pending; belum ada engine yang dipilih.

## Keputusan kode existing

Kode lama boleh dipakai ulang, diganti atau dihapus berdasarkan hasil [ARCHITECTURE-COMPARISON.md](ARCHITECTURE-COMPARISON.md). Tidak ada kewajiban mempertahankan arsitektur hanya karena sudah dibangun. Implementasi baru dimulai dari core backend terisolasi; belum ada kode baseline yang dihapus.


Akun Atlassian dan Jira IT-1 sudah tersedia; diagnostic read berhasil. Sisa setup identity/owner dan akses tercatat di [PHASES.md](PHASES.md). Runtime lokal terisolasi memiliki panduan di [deploy/README.md](deploy/README.md).
