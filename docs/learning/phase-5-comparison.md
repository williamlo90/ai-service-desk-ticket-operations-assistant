# Belajar dari perbandingan code-led dan n8n-led

Checkpoint ini menjalankan dua engine sungguhan, bukan sekadar membandingkan diagram.
Hasilnya sama untuk kontrak yang sudah diukur: masing-masing 14/14 skenario dasar
dan 17/17 saat kebijakan approval diubah menjadi lima menit.

## Urutan membaca kode

1. `backend/comparison/plans.py`: langkah kerja kandidat, tanpa expected results.
2. `backend/comparison/code_worker.py`: Python mengurutkan panggilan ke domain API.
3. `scripts/compare_orchestrators.py`, fungsi `workflow`: langkah yang sama menjadi
   node HTTP Request n8n. Tidak ada node yang menggandakan aturan approval.
4. `backend/comparison/server.py`: service bersama, aktor, fake clock, dan observasi.
5. `backend/comparison/target.py`: target independen yang menerima operasi lebih
   dahulu, lalu baru berhasil/gagal ketika event lingkungan diterapkan.
6. `backend/comparison/evaluate.py`: memeriksa urutan, database audit, target state,
   mutasi, denial, dan checkpoint. Expected results baru masuk di bagian ini.

## Pelajaran utama

`accepted` adalah receipt. Kasus baru boleh ditutup setelah hasil target cocok.
Timeout setelah efek terjadi tidak berarti tindakan boleh dikirim ulang.
Approval terikat pada snapshot dan versi policy; mengganti expiry saja belum
cukup bila approval lama seharusnya tidak berlaku lagi.

Perubahan target setelah kasus ditutup berbeda dari false closure. Evaluator
memeriksa kebenaran ketika transisi close terjadi, lalu memastikan evidence baru
menghasilkan reopen tanpa mengulang efek. Unit tests evaluator sengaja merusak
trace untuk memastikan false closure, audit mismatch, langkah hilang dan efek
ganda terdeteksi.

Kedua engine lulus skenario fungsional belum berarti keduanya setara untuk semua
operasi. Perbandingan 62 eksekusi memakai sequence eksplisit. Uji native wait
terpisah di bawah sudah lulus; retry dan effort pemeliharaan masih perlu dibandingkan.
Karena itu keputusan saat ini
adalah mempertahankan shared domain controls, belum memilih pemenang engine.

Baca [ADR 001](../architecture/ADR-001-orchestration-checkpoint.md) untuk keputusan
dan batas buktinya. William meminta checkpoint Phase 5 di-commit sebelum gate
akhir selesai; commit ini merekam hasil lokal yang sudah tervalidasi.

## Menjalankan ulang

Dari root proyek, dengan database proyek berjalan dan slot Docker tersedia:

```powershell
docker build -t service-desk-comparison:local -f backend/Dockerfile.comparison backend
& ./.venv/Scripts/python.exe -B scripts/compare_orchestrators.py
```

Prasyarat: .venv sudah berisi backend/requirements-postgres.txt; image n8n yang
dipin dalam script tersedia. Build context dibatasi oleh backend/.dockerignore.
Script tidak membaca .env, tidak menyunting instance n8n pengguna, dan tidak
membuka port host untuk fixture API. Database admin secret dipakai hanya di
container proyek untuk membuat/menghapus database uji; nilainya tidak ditampilkan.

Ringkasan tersimpan di docs/phase-5/orchestrator-comparison.json. Trace sintetis
dan export n8n yang sudah mengganti capability dengan placeholder berada di
local/comparison/<run-id> (diabaikan Git). Export tersebut adalah artefak belajar,
bukan workflow produksi yang siap diaktifkan tanpa konfigurasi.

[Referensi CLI n8n](https://docs.n8n.io/deploy/host-n8n/configure-n8n/use-the-command-line.md)
digunakan untuk import dan execute pada instance uji terpisah.

## Menunggu dan melanjutkan setelah restart

`backend/comparison/wait_worker.py` menyimpan checkpoint SQLite dan membaca state
domain sampai approval atau hasil target tersedia. Workflow dari
`scripts/native_wait_checks.py` memakai dua Wait node n8n: approval dan target.
Keduanya tidak memberikan approval atau menyelesaikan target sendiri.

Harness mematikan container engine secara mendadak pada kedua titik tersebut,
lalu menyalakannya kembali. Dua journey lulus empat restart total. Setelah event
eksternal diterima, verifikasi dan closure berjalan otomatis, dengan tepat satu
efek target per journey. n8n meneruskan execution ID yang sama; callback tanpa
token, callback tahap lama dan callback setelah selesai ditolak.

Pelajaran operasional: port terbuka belum berarti semua route siap. Harness
menunggu `/healthz/readiness` sebelum mengirim callback. Resume URL mengandung
token, sehingga hanya dipakai di memori dan container sementara, tidak dicetak
atau dimasukkan ke trace publik.

```powershell
& ./.venv/Scripts/python.exe -B scripts/compare_native_wait.py
```

Gunakan build dan prasyarat Docker di atas. Ringkasan ada di
[native-wait-comparison.json](../phase-5/native-wait-comparison.json); trace lokal
ada di `local/native-wait/<run-id>`. Uji ini mencakup satu alur access per engine;
database bisnis dan target tetap hidup. Distributed leases, retry/backoff,
skenario negatif native yang lebih luas, baseline parity dan effort pemeliharaan
masih menjadi pekerjaan berikutnya. Phase 5 tetap terbuka meskipun checkpoint sudah disimpan sesuai instruksi William.

## Recovery dan batas retry

`backend/service_desk/recovery.py` menyimpan jumlah percobaan, waktu percobaan
berikutnya, dan hasil akhir di state PostgreSQL. Code-led menjadwalkan timer di
`backend/comparison/recovery_worker.py`; n8n memakai HTTP Request → IF → Wait →
HTTP Request dari `scripts/recovery_checks.py`. Aturan bisnis tetap satu sumber.

Empat percobaan berarti satu pembacaan awal dan maksimal tiga percobaan ulang,
dengan jeda 1, 2, dan 4 detik. Yang diulang adalah pembacaan hasil target. Operasi
yang sudah diterima atau hasilnya belum diketahui tidak dikirim ulang. Approval
dicabut melalui kontrol supervisor sebelum dispatch; approval kedaluwarsa dan
dicabut masuk pemeriksaan manual tanpa tindakan target.

Pack recovery memeriksa tujuh kondisi per engine: expired approval, revoked
approval, hasil terlambat, kegagalan terminal, response hilang setelah efek,
dua timeout pembacaan sementara, dan batas retry habis. Fixture response hilang
menyiapkan operasi berstatus unknown sebelum scheduler dimulai; skenario gagal
dan read timeout juga menyiapkan target sebelum scheduler. Skenario terlambat dan
retry habis mencakup dispatch oleh scheduler. Expected results hanya dipakai evaluator.

Callback berulang atau terlambat menjadi petunjuk untuk read-back, bukan bukti
sukses. Setelah retry habis, completion yang terlambat boleh memperbarui evidence,
tetapi kasus tetap terbuka dan escalation tetap menunggu pemeriksaan manusia.
Ledger target menghitung efek dan jumlah panggilan submit secara terpisah.

```powershell
docker build -t service-desk-comparison:local -f backend/Dockerfile.comparison backend
& ./.venv/Scripts/python.exe -B scripts/compare_recovery.py
```

Lihat [hasil recovery](../phase-5/recovery-comparison.json). Escalation tersimpan
adalah antrean review pada state kasus; belum ada UI antrean atau notifikasi live.
Timer n8n di bawah 65 detik berjalan di proses dan pack ini tidak menguji crash
saat backoff. Budget tersimpan tidak dengan sendirinya menjamin timer akan bangun
setelah crash. Recovery transport HTTP, distributed leases, restart saat timer,
baseline parity dan effort pemeliharaan tetap perlu diuji sebelum memilih engine.

## Membandingkan dengan alur lama dan merawat policy

`scripts/check_baseline_regressions.py` memverifikasi checksum backup Phase 0,
menyalin source serta overlay ke folder lokal terisolasi, lalu menjalankan 11
file unit test lama: **47 tes lulus**. Environment file tidak disalin. Repository
lama tidak diubah. Ini membuktikan regresi lama tetap dapat dijalankan; fitur
billing/refund belum dipindahkan ke runtime service desk yang baru.

`scripts/measure_policy_change.py` mengubah satu entri policy pada dua salinan
source, menguji expiry 4:59/5:00 serta penolakan approval policy lama, lalu
mengembalikan perubahan. Hasil masing-masing 3/3, tanpa perubahan orchestrator
atau node workflow. Timer pengukuran mencatat kerja mesin, bukan waktu berpikir
atau editing manusia; angka itu tidak digunakan untuk menyatakan pemenang.

Baca matriks kesesuaian dalam [ADR 001](../architecture/ADR-001-orchestration-checkpoint.md).
Aturan keuangan, distributed leases, UI operator serta inbox/policy jobs lama
tetap dipertahankan sampai ada pengganti yang diuji atau keputusan scope baru
yang eksplisit. Kontrak v1 tidak diubah diam-diam.

```powershell
python -B scripts/check_baseline_regressions.py
python -B scripts/measure_policy_change.py
```

Script baseline membutuhkan lokasi backup Phase 0 dan interpreter baseline yang
tercantum di script. Keduanya tidak memulai database, provider atau layanan lama.

## Crash saat backoff yang tersimpan

```powershell
docker build -t service-desk-comparison:local -f backend/Dockerfile.comparison backend
& ./.venv/Scripts/python.exe -B scripts/compare_timer.py
```

Profil ini memakai jeda 70 detik agar Wait n8n disimpan ke database. Harness
mematikan engine setelah percobaan pertama, menyelesaikan target ketika engine
mati, lalu menyalakan kembali engine dan servicenya. Kedua kandidat lulus:
tidak ada percobaan terlalu awal, budget tetap dua percobaan, satu submit dan
satu efek. n8n melanjutkan execution ID yang sama tanpa panggilan webhook resume.

Lihat [timer-comparison.json](../phase-5/timer-comparison.json). Database bisnis
dan target tidak dimatikan. Kode dapat membaca due time kembali, tetapi konfigurasi
job masih diberikan oleh harness; belum ada deployment supervisor host. Profil
1/2/4 detik sebelumnya tetap fixture lab, belum terbukti pulih dari crash saat
timer pendek. Jangan menyamakan bukti timer 70 detik dengan semua jenis wait.
