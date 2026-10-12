# Compatibility — checked 2026-10-12

Separate installation layout, script execution, and a full creator workflow.

| Surface | Status | Evidence / remaining check |
|---|---|---|
| Codex project skill layout | Prepared; installer file checks passed | Canonical .agents/skills layout; skill validator passed |
| Claude Code project skill layout | Prepared; installer file checks passed | Same files copied into .claude/skills; live Claude workflow not run |
| macOS ARM64 media pipeline | Passed locally | Python 3.12.13, FFmpeg 7.1, pinned av/numpy/Pillow/bidi stack; behavioral tests and local render |
| Windows media pipeline | Targeted, not executed here | GitHub Actions matrix configured; await actual run |
| Linux media pipeline | Targeted, not executed here | GitHub Actions matrix configured; await actual run |
| Native browser/screen recording | Host-dependent | Requires an available permitted recording surface/tool |
| Audio listening/transcription | Host-dependent | No bundled universal speech model or claim of listening from a transcript |
| Native image/video generation | Host-dependent | Optional included host tools; no separate paid API |
| Premiere / DaVinci / CapCut project export | Outside default | Code/timeline project is the tested output type |

Python 3.12–3.13 is the target runtime. Initial local validation used 3.12.13. The pinned NumPy release requires Python >=3.12. A configured cross-platform CI workflow is not proof those jobs have run. A successful file-copy installer check is not a full agent behavior test.

Current skill paths and invocation are documented by [Codex](https://learn.chatgpt.com/docs/build-skills) and [Claude Code](https://code.claude.com/docs/en/skills). The skill doesn't itself create missing host tools or override their access controls.
