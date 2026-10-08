# Learning checkpoints

Phases 1–4 each have one commit. Phase 5 has a user-requested intermediate checkpoint; its final gate remains open. Use `git log --oneline` to locate the checkpoints and
`git show <commit> --stat` to see scope. Read each phase note before its tests.
Inspect historical files with `git show <commit>:path`; avoid resetting your
working tree while another phase is being implemented.

Phase 1 is the initial snapshot and includes work performed before the loop,
including older Docker evidence. Phase 2–4 contain the incremental changes.
Connected acceptance is deferred to Phase 5; no offline checkpoint closes it.

## Checkpoint belajar

| Phase | Fokus | Tes pada commit |
| --- | --- | --- |
| [1](phase-1.md) | Fondasi API, identitas dan lifecycle | 39 Python |
| [2](phase-2.md) | Journey dan target simulator | 53 Python |
| [3](phase-3.md) | SQL/Jira/callback adapter contracts | 62 Python |
| [4](phase-4.md) | MCP, client, skill dan AI adapter | 74 Python + 6 MCP |

Buka `git log --oneline --reverse` untuk empat commit. Pelajari dengan
`git show <commit> --stat`, lalu baca catatan phase dan tes yang relevan.
Tidak perlu menjalankan Docker atau membuka .env untuk belajar checkpoint ini.
Lanjutannya adalah [handoff Phase 5](../phase-5/HANDOFF.md).

Phase 5 sedang dikerjakan: baca [perbandingan code-led/n8n-led](phase-5-comparison.md)
untuk eksperimen 14 skenario, perubahan policy lima menit, native wait/restart,
dan tujuh skenario recovery per engine. Atas instruksi William, checkpoint
Phase 5 disimpan sekarang; gate arsitektur dan integrasi live belum lengkap.
