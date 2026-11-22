# Changelog — BD2 improvement package

**Baseline:** `os-bd1/main@0cb46da0c42eefd69121b81e9a889071bc309eb9`, examined using the GitHub connector. 

### Fixed in new standalone source

- Strict GET/POST validation, cap on request lengths, validated `depth` / `max` (no silent clamping).
- Strict `/proc/pid` protocol parser, including command names containing `]`, missing fields, mismatched queried PID, impossible child counts, mapped `502 BAD_OUTPUT`.
- Static file protection via `realpath` + `commonpath`, including symlink escape.
- Explicit `DEMO_LIMIT` after three active spawned process groups; thread-safe spawn / cleanup.
- Correct tree truncation signaling and `gone` only for process-exit errors.
- Generic internal HTTP error message (traceback in server stderr), no exception details leaked to client.
- UI real/mock badge, compact metrics, state colors, selected task, raw output, auto refresh, Reset.

### Documentation and review

- GitHub PR #3 original reviews mapped to Critical/Major decisions; self-audit documented separately.
- `docs/src/build_docs.py` patcher repairs escaped CODE / NameError and unescaped multiline syntax in the historical BD1 generator; requires running against actual repo to verify build.
- PDF documentation deps corrected: ReportLab + DejaVu Sans + qrcode, distinct from Python stdlib runtime.
- Manual, Final Report, single-page Poster and Teams post draft.

### Verified here

- New standalone Linux MOCK API suite: **21/21 PASS**.
- UI screenshot from live mock server displaying real Linux `/proc` process data.
- Three PDF outputs generated and visually checked (Poster=1 page, Final Report=5, Manual=4).

### Not yet done; do not report as done

- Applying bundle to GitHub (`create_branch` returned HTTP 403).
- Kernel module compile/load and Linux VM regression, original BD1 suite with REAL module.
- Official peer review PDF integration, real module screenshot, final release tag/URL and QR update.
