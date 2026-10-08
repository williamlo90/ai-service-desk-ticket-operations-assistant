# Architecture Comparison — 01 - AI Service Desk & Ticket Operations Assistant

Status: **hipotesis desain; belum ada benchmark pembanding**. User mengizinkan penggantian dan penghapusan kode jika solusi yang lebih baik membutuhkannya. Reuse adalah opsi, bukan kewajiban.

**Hipotesis awal:** n8n memimpin alur integrasi/triage/handoff; Python tetap service untuk policy checks, authorization, action transaction, outcome checks dan case state yang sensitif terhadap concurrency. Kandidat boleh memindahkan lebih banyak orchestration ke n8n jika lolos.

**Alur pembanding:** tiket masuk → konteks dan SOP → proposal → approval → action accepted → delayed result → verified outcome → close; kemudian event baru membuka kembali kasus. Jalur negatif mencakup wrong tenant, stale approval, duplicated event, worker/engine restart dan timeout setelah effect.

**Calon kode yang dapat dihapus setelah migrasi:** custom polling/scheduling, integration glue, orchestration wrapper dan wait/retry code yang sudah sepenuhnya diambil alih n8n. Tidak semua LangGraph/Celery otomatis diperlukan, tetapi job lain yang masih bergantung padanya harus dipetakan.

**Komponen yang harus memiliki pemilik eksplisit:** case state, immutable approvals, permissions, action idempotency, unknown-outcome reconciliation dan closure/reopen predicates. Implementasinya boleh diganti; invariants harus tetap terbukti.

## Kandidat yang dibandingkan

1. Baseline code-led: jalur existing dengan scope pembanding yang lengkap.
2. n8n-led orchestration + domain services: satu workflow utuh, bukan demo trigger kecil.
3. n8n-led dengan lebih banyak logic di workflow hanya jika scope dan kontrolnya dapat dipertanggungjawabkan; tidak wajib membangun ulang seluruh proyek sebagai eksperimen.

## Cara memutuskan

- [ ] Snapshot source, uncommitted changes, schema/data dan evidence yang dibutuhkan; inventaris dependencies dan in-flight jobs sebelum perubahan.
- [ ] Bekukan expected outcomes, acceptance gates, workload/hardware, data dan provider configuration yang sama. Baseline/kandidat dibandingkan pada fungsi setara; gap fitur existing tidak boleh memberi kemenangan semu.
- [ ] Jalankan happy path dan seluruh failure cases di atas. Critical authorization, atomicity, idempotency, verified outcomes dan recovery adalah hard gates; skor maintenance tidak menebus kegagalan kontrol.
- [ ] Ukur business correctness, manual touches, p95 end-to-end, achieved throughput, errors, operating cost/resources dan jumlah langkah recovery. Tidak mengklaim n8n lebih cepat/murah tanpa hasil.
- [ ] Berikan perubahan proses yang sama pada kedua kandidat (misalnya policy revision atau connector change); catat effort, bagian yang diubah, regression failures dan kemampuan operator mengikuti panduan.
- [ ] Pilih kandidat yang memenuhi semua hard gates dan memperbaiki masalah yang dinyatakan, dengan tradeoff tertulis. Lines-of-code lebih sedikit bukan satu-satunya ukuran.
- [ ] Catat keputusan per komponen: retain / replace / delete, pemilik state/retry, hasil benchmark, batas scope dan rencana migration/rollback.

## Migrasi dan penghapusan kode

- Bangun replacement pada branch/checkout yang dapat dibandingkan; jangan menjalankan kedua kandidat menulis side effect yang sama dalam shadow run. Gunakan read-only replay atau sandbox terpisah.
- Migrasikan schema/config dan in-flight jobs dengan cutover yang eksplisit. Hilangkan double schedulers dan double retry ownership.
- Setelah replacement lulus, hapus kode obsolete dari jalur aktif, tests yang hanya mengikat implementasi lama, dependencies dan dokumentasi lama yang tidak relevan. Pertahankan behavioral acceptance tests.
- Git snapshot/backup yang berguna cukup untuk rollback; public documentation fokus implementasi final, bukan sejarah migrasi.
- Jika prototype kalah atau tidak memberi manfaat, hentikan kandidat dan dokumentasikan keputusan singkat. Tidak wajib mempertahankan kode existing maupun n8n.
- Perbandingan dan migrasi dilakukan lokal/sandbox dahulu. Deployment cloud tetap Phase 9 terakhir.

Jadwal terbaru: implementasi bersama dan tes offline di Phase 1–4; prototype runtime setara dan keputusan arsitektur di Phase 5. Kontrak v1 tetap menjadi acuan perilaku. Belum ada benchmark kandidat atau penghapusan kode baseline.
