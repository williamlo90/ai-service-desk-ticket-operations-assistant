# Reusable Business Skills

Proyek 01: **AI Service Desk & Ticket Operations Assistant**

Tanggal rencana: 2026-10-08. Status: **empat paket skill v1 tersedia dan reuse offline teruji; perluasan bisnis/runtime masih pending**. Checklist hanya dicentang setelah artefak dan verifikasinya tersedia.

Skills di sini adalah paket kemampuan aplikasi yang dipakai assistant dan automation worker. Saat implementasi, setiap skill memiliki `skills/<name>/SKILL.md` beserta schema, implementation binding (Python handler atau n8n sub-workflow sesuai keputusan), dan tests; ini bukan sekadar kumpulan prompt atau asumsi bahwa sebuah Codex skill sudah terpasang.

| Skill | Input | Output | Batas tindakan |
| --- | --- | --- | --- |
| `triage_ticket` | pesan + metadata tiket | kategori, prioritas usulan, missing facts | read-only; tidak mengubah tiket |
| `prepare_resolution` | case + SOP + konteks | brief bersumber dan action proposal | approval sebelum perubahan |
| `verify_resolution` | action ID + hasil tujuan | verified/failed/unknown beserta bukti | unknown tidak menutup kasus |
| `summarize_operations` | rentang waktu + scope | laporan angka SQL dan penjelasan | read-only sesuai izin |

## Implementasi checkpoint offline

Paket v1 berada di [skills/manifest.json](skills/manifest.json), dengan SKILL.md,
input/output schema, fixtures dan binding `service_desk.skills.SkillRunner.run`.
Tabel di atas tetap target produk yang lebih luas. V1 menerima text untuk triage,
case_id/expected_version untuk prepare, case_id untuk verify, dan tanpa filter
untuk ringkasan jumlah kasus tenant. Priority recommendation, brief naratif serta
laporan rentang waktu SQL belum diimplementasikan. Verifikasi menulis audit.

Reuse interactive/automation dan scoped tenant kedua diuji di
backend/tests/test_ai_skills.py. Target model/provider tidak mempunyai jalur
untuk mengubah permission atau menyetujui action. Metrik bisnis live belum tersedia.

## Isi wajib setiap paket skill

- [x] SKILL.md: masalah bisnis, kapan dipakai/tidak dipakai, owner, preconditions, urutan langkah, exception handling, dan contoh.
- [x] Input/output JSON Schema berversi serta implementation binding Python atau n8n sub-workflow; aturan transaksi/izin tetap di service otoritatif dan tidak diduplikasi dalam prompt.
- [x] Declared tools dan permissions minimum; approval requirement dan side-effect classification.
- [x] Timeout, retries, idempotency, cancellation, postcondition check, dan compensation/manual recovery bila relevan.
- [x] Fixtures dengan normal/ambiguous/failure cases; expected results ditulis terpisah dari generation.
- [ ] Changelog/compatibility metadata dan metrik task correctness, latency, cost, serta error classification.

## Bukti reusable

- Skill yang sama dipanggil dari assistant interaktif dan automation worker tanpa menyalin core logic.
- Business/tenant configuration kedua menggunakan skill yang sama dengan policy/config berbeda.
- Menukar hosted model ke local model tidak mengubah aturan izin atau syarat approval.
- Skill gagal dengan status yang jelas jika data atau izin kurang; worker retry tidak menggandakan side effect.

**Selesai ketika:** semua skill tabel punya implementasi executable, kontrak, dokumentasi, dan tes; satu penggunaan ulang lintas caller dibuktikan dalam evidence.
