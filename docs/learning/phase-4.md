# Phase 4 — client, MCP, reusable skills, dan adapter AI

Tujuan checkpoint ini: menyiapkan jalur aplikasi dan kontrak AI tanpa memakai
Docker, membaca .env, atau memanggil Jira/provider live.

## Urutan belajar

1. Baca mcp-server/src/client.ts, lalu server.ts. Client melakukan handshake MCP,
   menemukan tools, dan memanggil tool. Server memvalidasi input serta output.
2. Ikuti backend.ts ke backend/service_desk/bridge.py. Identitas berasal dari
   konfigurasi operator; teks tiket tidak dapat mengubah actor, role, atau tenant.
3. Baca skills.py dan skills/manifest.json. Empat paket skill memakai handler
   yang sama untuk interactive dan automation; business rules tetap di service.
4. Baca ai.py. Adapter meminta data terstruktur, menyaring sumber sebelum prompt,
   memeriksa kutipan terhadap sumber yang diizinkan, dan tidak menjalankan action.
5. Baca test_ai_skills.py dan mcp-server/test/protocol.test.mjs. Bandingkan tes
   fungsi Python dengan tes client/server MCP yang benar-benar bertukar pesan.

## Hal yang dibuktikan

74 tes Python dan 6 tes Node/MCP lulus. Empat adapter (OpenAI, Claude, Grok,
Ollama) diuji dengan transport palsu. Input/output tidak valid, kutipan yang tidak
didukung, rate limit, penggunaan token yang tidak tersedia, cancellation, dan
penolakan fallback dari local-only diuji. Missing usage/cost bernilai null.

Skill triage, prepare, verify, summarize dipanggil melalui dua caller. Tenant beta
menggunakan binding yang sama dengan referensi SOP beta. Fixture dan expected
result tersedia di skills/fixtures.json. Ini scoped synthetic configuration,
bukan bukti onboarding bisnis kedua yang sudah selesai.

Tes MCP menjalankan proses Node dan Python, menguji proposal tanpa approval
ditolak, approval fixture terpisah dapat dipakai, receipt belum sama dengan hasil,
read-back memungkinkan penutupan, dan replay memakai operation ID yang sama.
Tidak ada tool untuk agent menyetujui tindakannya sendiri.

## Batas checkpoint

Tidak ada provider/model default atau benchmark AI. Retrieval masih lexical dan
source fixture, belum pgvector. Schema-valid exact quotes belum membuktikan
kesimpulan benar atau ketahanan prompt injection model nyata. Role/source filter
dan approval tetap ditegakkan kode meskipun teks meminta melewatinya.

Cancellation provider diperiksa sebelum dan sesudah transport; koneksi urllib
yang sedang berjalan tidak diputus secara aktif, dibatasi timeout 15 detik.
Timeout/cancellation bridge setelah dispatch adalah outcome unknown, tidak
membuktikan rollback. Tes runtime recovery tetap wajib.

MCP lokal memakai memory terpisah per proses, bukan PostgreSQL. Paket SDK dipin
untuk protocol 2025-11-25. Model/revision/license/hardware baru dipilih dan diuji
pada sesi integrasi/evaluasi. API WSGI intake dan bridge journey belum menjadi
satu deployment HTTP. React UI, identity lifecycle, worker durable dan orkestrator
terpilih adalah pekerjaan integrasi berikutnya, bukan hasil checkpoint ini.

## Menjalankan ulang

Dari backend: `python -B -m unittest discover -s tests -v`.
Dari mcp-server: `npm ci --ignore-scripts --no-audit --no-fund`, lalu `npm test`.
Install npm memerlukan registry; tes sesudah instalasi hanya proses lokal.
Jangan menjalankan deploy scripts untuk mempelajari checkpoint ini.

## Referensi kontrak provider

Ditinjau 2026-10-08; model tertentu tetap harus mendukung parameter yang dipakai.

- [OpenAI structured output](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Claude tool definition](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools)
- [Grok structured output](https://docs.x.ai/developers/model-capabilities/text/structured-outputs)
- [Ollama chat contract](https://docs.ollama.com/api/chat)

OpenAI/Grok menggunakan Responses structured output, Claude forced extraction
tool dengan validasi lokal, dan Ollama JSON Schema format. Kesetaraan kualitas
atau dukungan model belum diklaim dari mock tests.
