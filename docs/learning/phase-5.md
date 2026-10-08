# Phase 5 — integrasi lokal dan keputusan arsitektur

Fase ini ditutup setelah 130 tes Python, 8 tes Node dan gate connected lokal lulus.
Commit 66693e6 adalah checkpoint yang diminta William di tengah fase; commit
penutupan menyimpan implementasi lanjutannya beserta bukti akhir.

## Yang bisa dipelajari

1. **Approval bukan dispatch.** William meninjau proposal di browser; identitas
   staff terpisah menjalankan tindakan. Persetujuan terikat tenant, payload,
   versi dan masa berlaku, lalu hasil target dibaca ulang sebelum kasus ditutup.
2. **Receipt bukan hasil.** Respons hilang tidak berarti tindakan gagal. Operation
   ID dan journal tersimpan mencegah pengiriman ulang tanpa rekonsiliasi.
3. **Idempotency lintas proses.** PostgreSQL CAS melindungi perubahan state dan
   audit; advisory lock mengoordinasikan recovery worker yang kooperatif.
4. **Jira tetap sumber tiket.** Snapshot diimpor dengan identitas deterministik.
   Source drift meminta review; polling hanya membaca key yang diizinkan.
   Ticket-link dan metadata hasil punya read-back dan pemeriksaan replay sendiri.
5. **Scope token memengaruhi endpoint.** Library mendukung scoped gateway dan
   site origin eksplisit. Lab menggunakan token tanpa scope atas pilihan William;
   kredensial hanya dimuat internal dan tidak masuk Git/log/chat.
6. **Keputusan engine harus menjelaskan ownership.** Dua engine lolos reference
   pack. Code-led dipilih karena kontrol domain dan state sudah ada di Python/SQL,
   sehingga operasi V1 lebih sederhana. Tidak ada klaim benchmark kecepatan atau
   effort manusia yang tidak diukur. Detail: ADR 003.
7. **Pemulihan harus diuji.** API/worker dihentikan dan pulih otomatis; job
   sintetis dipindah antar database lalu rollback dengan satu efek target.
   Ini bukan bukti host recovery, fencing network partition, atau release cloud.

## File utama

- `backend/service_desk/worker.py`, `recovery.py`, `postgres.py`: job dan state.
- `jira_search.py`, `jira_links.py`, `jira_result.py`: integrasi Jira terbatas.
- `scripts/operator_service.py`: supervisor API/worker/poller.
- `scripts/check_phase5_gate.py`: pemeriksaan akhir dan hash sumber.
- `docs/phase-5/phase5-gate.json`: hasil akhir; report lain memberi bukti rinci.
- `docs/architecture/ADR-003-selected-code-led.md`: keputusan dan tradeoff.

Tahap berikutnya: Phase 6 mengevaluasi model nyata, kualitas keputusan dan manfaat
bisnis dengan dataset/rubrik yang dibekukan. Fase ini tidak mengklaim ROI atau
akurasi model dari tes deterministik.
