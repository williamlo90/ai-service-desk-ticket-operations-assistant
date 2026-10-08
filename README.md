# AI Service Desk & Ticket Operations Assistant

Service desk assistant untuk mengubah tiket Jira menjadi tindakan yang disetujui
manusia, hasil yang diverifikasi di sistem tujuan, dan audit yang tersimpan.

**Status: Phase 7 dan 8 selesai untuk rilis dan handover lab lokal.**
[Gate handover](docs/phase-8/phase8-gate.json) lulus. Mulai dari
[panduan operator](docs/phase-8/HANDOVER.md) atau jalankan demo tanpa kredensial:
`python scripts/demo_handover.py`.

AI memberikan rekomendasi langkah berikutnya beserta alasan; keputusan tetap pada
operator. OpenAI lulus 16/16 held-out sintetis. Ollama tetap eksperimental;
Claude/Grok dan Azure ditunda.

## Arsitektur yang dipilih

**Code-led:** Python domain service + PostgreSQL, TypeScript MCP, halaman approval
browser, adapter Jira/Keycloak/service demo, serta supervisor proses lokal.
[ADR 003](docs/architecture/ADR-003-selected-code-led.md) mencatat keputusan atas
otoritas yang diberikan William, bukti pembanding, alasan dan tradeoff. n8n tetap
tersedia sebagai integrasi pendukung; workflow existing tidak dihapus.

PostgreSQL menyimpan proposal, approval yang terikat versi/payload, operation ID,
retry state dan audit. Worker hanya memproses job yang memiliki approval tersimpan.
Target read-back menentukan keberhasilan; respons accepted saja tidak menutup
kasus. Source drift dan hasil yang tidak pasti masuk review.

Jira memakai polling HTTPS terautentikasi dengan scope key yang dibatasi dan
pagination berbasis cursor. Runtime lokal tidak membuka receiver webhook publik.
API berjalan di loopback; supervisor memulihkan child process, bukan host reboot.

## Bukti yang sudah tersedia

- **182 tes Python, 8 tes MCP dan 14 pemeriksaan JavaScript lulus** dari instalasi sumber bersih Phase 8.
- Perbandingan dua engine: masing-masing 14 kasus dasar dan 17 kasus policy v2;
  pack recovery, transport dan native wait/restart tercatat terpisah.
- PostgreSQL nyata: migration replay, RLS, CAS, audit atomicity dan pemulihan proses.
- Dua tenant Keycloak/service demo: akses grup, restart service, tiga health check
  berjarak waktu nyata, serta replay tanpa efek ganda.
- [Approval William](docs/phase-5/human-approved-access.json): IT-1 diimpor,
  disetujui di browser, akses Keycloak diberikan dan diverifikasi, kasus lokal ditutup.
- [Ticket-link dan polling](docs/phase-5/jira-connected-check.json): IT-2 dibuat,
  relasi dengan IT-1 diverifikasi, pencarian dua halaman serta sinkronisasi ulang
  lulus. Poller aktif setiap 60 detik untuk kedua tiket lab tersebut.
- [Metadata hasil Jira](docs/phase-5/jira-result-write.json) ditulis dan dibaca ulang;
  replay tidak membuat PUT tambahan. Status workflow Jira tidak diubah.
- [Supervisor](docs/phase-5/operator-supervisor-check.json) memulihkan API/worker
  setelah crash dengan kasus dan entitlement tetap utuh.
- [Migration/rollback](docs/phase-5/operator-migration-check.json) dan
  [job cutover](docs/phase-5/job-cutover-check.json) terisolasi lulus, dengan satu
  efek target pada perpindahan dan rollback job sintetis.

Hasil tersebut merupakan validasi lab. Alur OpenAI diterima William; evaluasi memakai
data sintetis dan pilot manusia bersifat diagnostik. Tidak ada klaim ROI, performa produksi
atau deployment cloud. Approval fixture diberi label dan
tidak disamakan dengan approval manusia. Baseline billing/refund dipertahankan;
47 tes regresinya telah dijalankan terpisah, tanpa klaim bahwa job itu sudah dipindah.

## Mulai dan pelajari

1. Baca [rencana fase](PHASES.md), [handover terkini](docs/phase-8/README.md)
   dan [panduan operator](docs/phase-5/OPERATOR-LAB.md).
2. Tes Python: dari `backend`, jalankan
   `../.venv/Scripts/python.exe -B -m unittest discover -s tests`.
3. Tes MCP: dari `mcp-server`, jalankan `npm test` setelah dependency terkunci terpasang.
4. Jalankan `./scripts/operator-service.ps1 Start`, `Stop`, atau `Status` untuk
   runtime proyek ini. Lihat [setup](deploy/README.md) untuk database dan target.
5. Gunakan [catatan belajar](docs/learning/README.md) dan commit per fase untuk
   mempelajari perubahan. Commit `66693e6` adalah checkpoint Phase 5 atas permintaan
   William; commit penutupan Phase 5 mencatat gate yang sudah lulus.

Kredensial dimuat skrip secara internal dan tidak ditampilkan. Private runtime
config berada di luar repository; `.env`, data runtime dan snapshot lokal tidak
masuk Git. Jangan menjalankan tes pencabutan akses terhadap entitlement operator
yang sedang aktif; gunakan fixture terpisah.

## Tahap selanjutnya

Gunakan lab melalui panduan handover dan periksa `scripts/operator_health.py`
sebelum sesi. Phase 7 menguji kegagalan kritis dan 48 alur HTTP sintetis; Phase 8
memverifikasi instalasi sumber bersih dan demo. Hasil ini tidak menyatakan layanan
siap produksi. Azure tetap Phase 9 dan belum dimulai.
