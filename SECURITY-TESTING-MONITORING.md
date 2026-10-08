# Access Control, Testing, Monitoring & Documentation

Proyek 01: **AI Service Desk & Ticket Operations Assistant**

Tanggal rencana: 2026-10-08. Status: **rencana implementasi; belum ada implementasi baru dalam folder ini**. Checklist hanya dicentang setelah artefak dan verifikasinya tersedia.

## Access control sejak awal

| Role | Izin minimum |
| --- | --- |
| Operator | Membaca scope sendiri, menjalankan assistant, membuat proposal |
| Approver | Menyetujui tindakan dalam batas kewenangan; approval terikat payload/version |
| Administrator | Mengelola koneksi, policy, roles, model/runtime; tidak otomatis memperoleh hak approval bisnis |
| Auditor | Membaca audit/evidence yang disanitasi; tidak mengeksekusi action |
| Worker/service account | Hanya skill/tools dan tenant yang ditugaskan |

Pisahkan tenant dan object-level authorization pada API, MCP, workers, retrieval, cache, export, dan logs. Untuk tindakan penting terapkan pemisahan pengusul/approver sesuai policy. Test environment tidak mengakses data produksi dan destructive tests hanya ke database disposable.

## Kasus wajib spesifik proyek

- [ ] Salah hubungkan tiket ke pelanggan atau tenant lain
- [ ] SOP lama bertentangan dengan SOP yang berlaku
- [ ] Approval stale setelah fakta berubah
- [ ] API accepted tetapi tindakan kemudian gagal
- [ ] Timeout setelah tindakan berhasil; retry tidak menggandakan efek
- [ ] Callback terlambat/duplikat, dua petugas mengubah kasus bersamaan
- [ ] Kasus ditutup lalu muncul bukti baru; reopen dengan audit

## Lapisan testing

- [ ] Unit: aturan bisnis, schemas, matching/parsing, transitions, permissions, evaluator semantics.
- [ ] Contract: provider, custom MCP protocol, platform API, migrations, skill versions.
- [ ] Integration: PostgreSQL nyata terisolasi, queue/worker, approval/execute/verify, sandbox platform.
- [ ] End-to-end: operator menjalankan UI/client sampai outcome tujuan; negative tests memanggil API langsung.
- [ ] AI quality: frozen labels, held-out cases, wrong/missing evidence, prompt injection, unsupported claims, abstention, regressions.
- [ ] Reliability: duplicate events, lost response, concurrent writes, worker interruption, resource exhaustion, restore dan rollback.

## KPI dan alat ukur

triage accuracy per kategori; policy-correct decision rate; verified resolution rate; false closure rate; auto-resolution coverage dari seluruh kasus; manual touches; reopen rate; p95 sampai hasil terverifikasi; biaya per kasus benar.

Setiap report menyertakan code revision dan dirty diff fingerprint bila ada, dataset/version/hash, model/provider/runtime, environment/hardware, workload, durations, sample counts, excluded records beserta alasan, serta expected/observed results. Jangan menggabungkan benchmark berbeda menjadi satu persentase.

Tetapkan workload normal, peak, soak, batas error, resource budget, dan stop conditions sebelum run. p50/p90/p95/p99 dilaporkan per operasi dengan N dan distribusi status; satu upload bukan bukti distribusi tail latency. Ukur achieved rate/dropped work, queue wait, processing completion, dan correctness. Concurrency test harus membuktikan jumlah final effects yang tepat, bukan sekadar semua respons 200/409.

## Monitoring dan troubleshooting

- [ ] Correlation ID dari request sampai outcome; structured logs dengan redaction; metrics untuk errors, queue age, stale sync, model/schema failure, latency, resource usage, dan cost.
- [ ] Business metrics untuk verified completion, review/escalation, false closure/false hold jika relevan, dan perubahan kualitas per versi.
- [ ] Alert test: trigger incident terkontrol, buktikan notification diterima, dan dokumentasikan tindakan operator.
- [ ] Runbook untuk provider outage, expired platform token, failed sync, stuck job, unknown write, database restore, model rollback, dan duplicate incident.
- [ ] Retention dan akses logs/evidence/feedback jelas; raw sensitif disimpan terbatas, public evidence disanitasi.

## Release gate

- Nol bypass izin, cross-tenant leakage, duplicate side effect, dan false-success pada critical scenario suite yang ditetapkan. Nol pada suite terbatas tidak berarti jaminan nol di seluruh produksi.
- Quality thresholds ditentukan per risiko sebelum final evaluation; laporkan coverage serta kasus yang gagal.
- Local evidence lulus pada Phase 7; cloud-runtime evidence baru dijalankan pada Phase 9.
- Test yang gagal diselesaikan atau scope dikoreksi dan diverifikasi; tidak menurunkan gate diam-diam setelah melihat hasil.

## Acceptance automation yang dipilih

Uji workflow n8n sesuai [N8N-AUTOMATION.md](N8N-AUTOMATION.md): duplicate/out-of-order events, authorization, stale approvals, unknown writes, replay, notification delivery, retention dan restore. Validasi hasil bisnis terpisah dari status node.
