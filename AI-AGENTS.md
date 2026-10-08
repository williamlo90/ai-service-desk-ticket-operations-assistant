# AI Agents, Assistants & Bots

Proyek 01: **AI Service Desk & Ticket Operations Assistant**

Tanggal rencana: 2026-10-08. Status: **rencana implementasi; belum ada implementasi baru dalam folder ini**. Checklist hanya dicentang setelah artefak dan verifikasinya tersedia.

## Tugas assistant

Mengubah tiket masuk menjadi pekerjaan yang jelas, tindakan yang disetujui, dan hasil penyelesaian yang terverifikasi.

Pengguna: Service desk lead dan support specialist.

Alur: Tiket Jira masuk → klasifikasi dan pengumpulan konteks → retrieval SOP → rencana tindakan → approval sesuai risiko → update/action → periksa hasil di sistem tujuan → tutup atau eskalasi → laporan.

## Kemampuan yang dibangun

- Mulai dari tiga kasus MSP: permintaan akses dengan approval, gangguan layanan dengan SOP diagnosis, dan tiket berulang yang perlu dikaitkan. Definisikan hasil selesai untuk masing-masing.
- Triage pesan mentah menjadi kategori, prioritas, owner yang diusulkan, dan informasi yang kurang; kasus ambigu meminta klarifikasi.
- Ambil konteks tiket dan SOP sesuai tenant, role, versi efektif, dan waktu kejadian. Brief mengutip fakta dan sumber, bukan menebak.
- Pisahkan action requested/accepted/running/succeeded/failed/unknown. Penutupan memerlukan bukti hasil atau alasan penyelesaian tanpa action yang terstruktur.
- Tambahkan reopen, delayed events, escalation SLA, dan bounded automation untuk tindakan berisiko rendah yang diizinkan.
- Buat laporan backlog, pelanggaran SLA, manual touches, dan reopen dari data SQL; AI hanya menjelaskan hasil yang bersumber.

## Kontrak perilaku

- Input membawa task ID, authenticated actor, tenant, permitted scope, dan referensi data. Scope berasal dari server, bukan dipercaya dari prompt.
- Output minimal: status, facts dengan source references, missing information, proposed actions, reason, dan confidence jika memiliki makna terkalibrasi. Confidence sendiri tidak memberi izin eksekusi.
- Tools dan jumlah langkah dibatasi; ada timeout/cancellation dan terminal state. Tugas di luar kemampuan menghasilkan klarifikasi atau eskalasi.
- Business rules, arithmetic, permissions, approval dan state transitions ditegakkan domain service Python.
- Prompt tidak memuat credentials. Evidence dari dokumen/pesan dianggap input tidak tepercaya, bukan instruksi untuk memperluas akses.
- Bedakan recommendation, approved, dispatched, accepted, verified, failed, dan unknown sesuai kebutuhan proyek. Jangan mengklaim action berhasil hanya dari teks model.
- Mulai satu orchestrator dan skills deterministik. Multi-agent hanya jika pemisahan tanggung jawab memberi manfaat terukur.

## Artefak implementasi yang harus ada

- [ ] Workflow dengan typed contracts, durable state dan recovery path; orchestration mengikuti keputusan proyek (Python atau n8n), bukan wajib dua engine.
- [ ] Assistant UI/reference client TypeScript dengan preview bukti, proposal, approval dan status.
- [ ] Prompt/schema/version registry serta adapters hosted/local.
- [ ] Scenario tests untuk happy path, ambiguous input, refusal/abstention, injection, dan tool failure.
- [ ] Run trace yang menghubungkan input, model/skill/tool versions, approval, hasil tujuan, latency, dan biaya tanpa membocorkan secrets.

**Selesai ketika:** operator dapat menjalankan demo pada PROJECT-DELIVERY.md; hasil diperiksa terhadap reference outcome; kegagalan tidak ditampilkan sebagai sukses.

## Pemilik orchestration

Pakai n8n untuk integrasi workflow; evaluasi perluasan ownership lewat prototype. Tiket masuk, pengambilan konteks lintas aplikasi, routing, pengingat SLA, dan reporting. Domain service menjaga permissions, case state, approved actions, outcome verification dan reopen. Hybrid sebagai hipotesis awal. Bandingkan orchestration Python existing dengan n8n-led pada satu alur kasus utuh; orchestration lama boleh dihapus jika kandidat menang. Lihat [N8N-AUTOMATION.md](N8N-AUTOMATION.md).
