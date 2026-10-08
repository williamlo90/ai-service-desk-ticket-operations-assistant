# Learning checkpoints

Phases 1–4 each have one commit. Phase 5 has a user-requested intermediate checkpoint; its final local V1 gate has now passed. Use `git log --oneline` to locate the checkpoints and
`git show <commit> --stat` to see scope. Read each phase note before its tests.
Inspect historical files with `git show <commit>:path`; avoid resetting your
working tree while another phase is being implemented.

Phase 1 is the initial snapshot and includes work performed before the loop,
including older Docker evidence. Phase 2–4 contain the incremental changes.
Connected acceptance was completed in Phase 5; earlier offline checkpoints did not close it.

## Checkpoint belajar

| Phase | Fokus | Tes pada commit |
| --- | --- | --- |
| [1](phase-1.md) | Fondasi API, identitas dan lifecycle | 39 Python |
| [2](phase-2.md) | Journey dan target simulator | 53 Python |
| [3](phase-3.md) | SQL/Jira/callback adapter contracts | 62 Python |
| [4](phase-4.md) | MCP, client, skill dan AI adapter | 74 Python + 6 MCP |

Buka `git log --oneline --reverse` untuk urutan commit per fase. Pelajari dengan
`git show <commit> --stat`, lalu baca catatan phase dan tes yang relevan.
Tidak perlu menjalankan Docker atau membuka .env untuk belajar checkpoint ini.
Lanjutannya adalah [handoff Phase 5](../phase-5/HANDOFF.md).

Phase 5 selesai untuk integrasi lab; baca [perbandingan code-led/n8n-led](phase-5-comparison.md)
untuk eksperimen dan [catatan penutupan](phase-5.md) untuk hasil akhirnya.
Checkpoint antara disimpan atas instruksi William; status akhirnya ada pada gate Phase 5.

Sandbox lanjutan: Keycloak memisahkan tenant dalam realm, sedangkan adapter
membatasi user/grup yang boleh diubah. Service demo menjalankan child process
nyata agar restart dapat dibuktikan lewat perubahan generation. Pelajari
[setup sandbox](../../deploy/README.md#keycloak-and-demo-targets) dan
[bukti connected](../phase-5/lab-connected-check.json). Approval fixture menguji
mekanisme; approval William yang sebenarnya tercatat terpisah pada hasil Phase 5.


Keputusan akhir orchestration V1 kini **code-led**, melalui delegasi William.
Baca [ADR 003](../architecture/ADR-003-selected-code-led.md): keputusan berangkat
dari ownership state dan kompleksitas operasi, bukan klaim pemenang benchmark.
Runtime memiliki worker approval-aware, supervisor child process, pencarian Jira
berpaginasi dan adapter related-ticket. Gate live terakhir dan status commit
tercantum di [CURRENT-GATES](../phase-5/CURRENT-GATES.md).

[Catatan penutupan Phase 5](phase-5.md) merangkum implementasi dan bukti akhir.

[Catatan Phase 6](phase-6.md) menjelaskan evaluasi model, rekomendasi langkah
berikutnya, pilot manusia dan batas klaim. [Status terkini](../phase-6/CURRENT.md)
menjadi acuan hasil dan pekerjaan selanjutnya.
