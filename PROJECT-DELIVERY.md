# Project Delivery — Panduan untuk Manusia

Proyek 01: **AI Service Desk & Ticket Operations Assistant**

Tanggal rencana: 2026-10-08. Status: **rencana implementasi; belum ada implementasi baru dalam folder ini**. Checklist hanya dicentang setelah artefak dan verifikasinya tersedia.

## Penjelasan satu kalimat

Mengubah tiket masuk menjadi pekerjaan yang jelas, tindakan yang disetujui, dan hasil penyelesaian yang terverifikasi.

**Siapa yang memakai:** Service desk lead dan support specialist.

**Pekerjaan sehari-hari:** Tiket Jira masuk → klasifikasi dan pengumpulan konteks → retrieval SOP → rencana tindakan → approval sesuai risiko → update/action → periksa hasil di sistem tujuan → tutup atau eskalasi → laporan.

## Demo penerimaan

Tampilkan satu tiket rutin yang selesai terverifikasi, satu tiket yang harus meminta approval, dan satu tindakan berstatus unknown yang tetap terbuka sampai rekonsiliasi.

Demo menggunakan data sintetis/test tenant. Tunjukkan input, bukti, keputusan, tindakan, hasil, dan cara menangani kegagalan. Jangan hanya memperlihatkan chat yang menjawab dengan lancar.

## Dokumen delivery yang dibuat saat implementasi

- [ ] Business brief satu halaman: masalah, owner, scope, hasil yang diukur, dan batas kemampuan.
- [ ] Quick start: prerequisites, install lokal, seed demo, login roles, startup/shutdown, dan uninstall/cleanup.
- [ ] User guide berbahasa English: langkah penggunaan dengan contoh dan screenshot, istilah sederhana, arti setiap status, serta kapan harus meminta bantuan.
- [ ] Acceptance checklist: tugas, hasil yang diharapkan, hasil aktual, evidence, pass/fail; bisa dijalankan sendiri tanpa merekrut demo tester.
- [ ] Runbook operator: kegagalan umum, langkah diagnosis, pemulihan, eskalasi, backup/restore, serta rollback.
- [ ] Release/evidence manifest: commit, data/model/config versions, tests, integrations yang benar-benar diuji, limitations yang relevan.
- [ ] Demo singkat dan case study dengan hasil terukur yang benar; single-operator/synthetic tetap dinyatakan sesuai lingkup.
- [ ] Handover: pemilik credentials/config, permissions, biaya operasi/asumsi, retention, support owner, dan jadwal pemeliharaan.
- [ ] Cloud deployment appendix setelah Phase 9: environment, health, monitoring, recovery proof, teardown/ongoing ownership.

## Ongoing support

- Periksa failed jobs, unknown outcomes, stale sync, resource/cost alerts dan review queues pada cadence yang sesuai beban.
- Review feedback/error clusters dan tambahkan regression cases setelah insiden.
- Setiap perubahan prompt/model/skill/policy/platform API memicu pengujian yang relevan sebelum release.
- Perbarui dokumen dan runbook agar sesuai aplikasi; simpan sejarah eksperimen lokal bila berguna, public narrative fokus hasil tervalidasi.

## Definisi selesai

Seorang operator dapat memahami manfaatnya, menjalankan tugas normal, mengenali kasus yang harus ditinjau, menemukan bukti hasil, dan mengikuti pemulihan menggunakan dokumentasi. Local-ready, connected-sandbox-validated, offline-delivered, dan cloud-validated adalah status berbeda; hanya gunakan yang sudah dibuktikan.

## Delivery automation

- [ ] Sertakan export n8n tersanitasi, panduan import, credentials, schedule/timezone, activation/deactivation dan recovery.
- [ ] Demonstrasikan workflow target beserta failure/replay; hubungkan run ID dengan verified business outcome.
