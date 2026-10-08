# Local AI Deployment & Model Providers

Proyek 01: **AI Service Desk & Ticket Operations Assistant**

Tanggal rencana: 2026-10-08. Status: **rencana implementasi; belum ada implementasi baru dalam folder ini**. Checklist hanya dicentang setelah artefak dan verifikasinya tersedia.

## Profil yang wajib tersedia

| Profil | Implementasi | Bukti selesai |
| --- | --- | --- |
| OpenAI | API adapter dengan tool calling/structured output sesuai kemampuan model | contract test + bounded real canary pada data yang diizinkan |
| Claude | API adapter dengan kontrak output aplikasi yang sama | contract test + bounded real canary pada data yang diizinkan |
| Grok | API adapter dengan kontrak output aplikasi yang sama | contract test + bounded real canary pada data yang diizinkan |
| Local | Ollama sebagai baseline; seluruh model artifact dicatat | inference nyata lokal + quality/performance report + failure recovery |

API integration memakai API resmi, bukan otomatisasi UI ChatGPT/Claude. Tidak wajib menggunakan tiga provider sekaligus dalam satu request. Pilih default berdasarkan hasil benchmark, dan catat capability gap tiap model secara eksplisit. Jika native structured output/tool calling tidak tersedia, validasi schema tetap wajib dan jalur yang belum memenuhi kontrak tidak dinyatakan setara.

Local profile memakai Ollama dan model/embeddings lokal; hosted profile memakai provider yang dipilih. Mode local-only harus menolak fallback ke provider eksternal. Business platform SaaS dapat membutuhkan internet; kemampuan inference lokal tidak otomatis berarti seluruh sistem offline.

## Checklist runtime lokal

- [ ] Catat CPU/GPU/RAM/VRAM, model/license/revision, quantization, context size, runtime version, dan batas concurrency.
- [ ] Sediakan setup Linux/Docker, health/readiness, warm-up, cancellation, request size limits, dan timeout.
- [ ] Model/embedding/tokenizer artifacts dipin dan diverifikasi; jelaskan provisioning awal yang memerlukan download.
- [ ] Uji malformed output, hallucination, input panjang, OOM, unavailable runtime, dan safe degradation.
- [ ] Bandingkan kualitas, end-to-end latency, resources, serta biaya asumsi hosted/local pada tugas yang sama.
- [ ] Dokumentasikan upgrade, rollback, caching, data retention, dan mekanisme menghapus data/model jika diperlukan.

llama.cpp dan vLLM adalah alternatif runtime sesuai hardware, bukan kewajiban memasang tiga inference server pada semua proyek. Proyek 07 membandingkan llama.cpp dengan baseline dan menambahkan vLLM hanya jika hardware kompatibel tersedia; ketidaktersediaan GPU bukan bukti vLLM sudah diuji.

## Evaluation yang adil

- Pisahkan mocked/stubbed load tests, real-provider canary, dan local-model evaluation.
- Laporkan model/runtime/hardware, sample count, schema success, correctness, latency, token usage bila tersedia, dan biaya dengan sumber/asumsi harga saat run.
- Jangan otomatis mengganti provider pada workflow side-effecting tanpa idempotency dan pemeriksaan hasil yang sudah terjadi.
- Keys yang belum tersedia membuat provider live validation pending; pekerjaan lokal tetap bisa lanjut.

**Selesai ketika:** seluruh adapter terimplementasi, integration status jujur per provider, dan satu local model benar-benar menjalankan workflow. Requirement pengalaman ketiga API baru penuh ketika masing-masing punya canary nyata yang lulus; khusus 07 canary hosted terisolasi dari mode privat.
