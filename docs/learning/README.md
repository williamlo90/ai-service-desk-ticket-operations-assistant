# Learning checkpoints

Each phase is one commit. Use `git log --oneline` to locate the checkpoints and
`git show <commit> --stat` to see scope. Read each phase note before its tests.
Inspect historical files with `git show <commit>:path`; avoid resetting your
working tree while another phase is being implemented.

Phase 1 is the initial snapshot and includes work performed before the loop,
including older Docker evidence. Phase 2–4 contain the incremental changes.
Connected acceptance is deferred to Phase 5; no offline checkpoint closes it.
