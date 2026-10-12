# Video Edit

[![Media pipeline](https://github.com/aarefhosseini/ai-video-edit-skill/actions/workflows/test.yml/badge.svg)](https://github.com/aarefhosseini/ai-video-edit-skill/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A free, open-source skill for creating polished short videos in Codex and Claude Code.

[راهنمای فارسی](docs/README.fa.md) · [Compatibility](docs/compatibility.md) · [Product scope](docs/product-spec.md)

Give your agent the footage, destination, and references. It asks the missing questions, studies relevant examples, proposes an edit, prepares a complete visual preview, and produces local exports. The creator works through conversation; the agent handles setup and media commands.

Version: **0.1.0 beta**. The local media pipeline has behavioral tests; browser recording, generation, listening, and reference access depend on tools available to the host agent. Full host/OS compatibility is tracked separately from Python tests.

## What it does

- Ideas, reference analysis, scripts, recording guidance, take selection, editing, covers, captions, carousels, and analysis of supplied post-publication data.
- Raw cut lists with pitch-preserving speed adjustments and optional color/audio cleanup.
- Real footage and screen recordings, source crops, face/media framing, Persian/RTL and English captions, backgrounds and motion previews.
- Guided mode with complete-preview approval, or automatic execution inside an agreed brief.
- Locked-master compositing with exact audio-payload, timestamp and decoded-sample checks.
- MP4, SRT when requested, review reports, and an editable code/timeline project.

The skill optimizes clarity, pacing, and shareability. It does not guarantee virality. It excludes long-form production, publishing and account management. Native Premiere/DaVinci/CapCut projects are not a built-in export.

## Start without terminal work

Give your agent this link: https://github.com/aarefhosseini/ai-video-edit-skill and ask:

> Install this repository's video-edit skill into my selected project for Codex (or Claude Code). Prepare its local media runtime, then ask what I want to make, where it will appear, and whether I want guided or automatic production. Use no separate paid API.

Provide an existing project directory if the agent needs one. The installer refuses to overwrite an existing skill. Once installed, invoke `$video-edit` in Codex or `/video-edit` in Claude Code, or ask naturally for a short-video edit.

Example:

> Make an Instagram video from these takes and the real product recording. Use the reference for framing, keep my voice and identity, use readable Persian captions, and show every section and transition before the final export. My colors are navy and warm white.

For a selected master:

> Use this approved master. Preserve the cuts, speed, retouch, and audio exactly. Add the real screen footage while I discuss each feature. Work automatically within this brief and report anything you couldn't verify.

## Installation details for agents/maintainers

The canonical skill is `.agents/skills/video-edit/`. Repository-scoped discovery and invocation follow the [Codex skill documentation](https://learn.chatgpt.com/docs/build-skills) and [Claude Code skill documentation](https://code.claude.com/docs/en/skills).

```sh
python install.py --agent codex --project /path/to/project
python install.py --agent claude --project /path/to/project
```

On Windows, use the selected Windows project path. The same skill is copied into `.agents/skills/video-edit` for Codex or `.claude/skills/video-edit` for Claude Code. No account configuration or unrelated skills are changed.

## Local execution

Python 3.12–3.13 and the pinned requirements are used by the bundled renderer. FFmpeg is discovered from `FFMPEG`, PATH, or the executable supplied by `imageio-ffmpeg`. The agent should use an isolated environment in the working project. Package installation needs internet on an unprepared machine; rendering requires no paid API. The host agent's own subscription/usage and media processing policies still apply.

```sh
python -m venv .venv
# macOS/Linux interpreter: .venv/bin/python
# Windows interpreter: .venv/Scripts/python.exe
.venv/bin/python -m pip install -r .agents/skills/video-edit/scripts/requirements.txt
.venv/bin/python .agents/skills/video-edit/scripts/media.py doctor
```

The bundled compositor supports a focused set of layout controls. Advanced tracking, retouch masks, audio mixing and custom motion are implemented by the agent in a project-local renderer when needed, using the editing references. The skill never assumes that an unavailable host tool exists or silently introduces a paid service.

## Reproducible demo and checks

The demo uses generated test patterns, a synthetic tone and a drawn illustration. It contains no customer data, real-person footage or redistributed font.

```sh
python examples/make_demo.py demo-output
python .agents/skills/video-edit/scripts/composite.py preview demo-output/plan.json --output demo-output/review
python .agents/skills/video-edit/scripts/composite.py motion demo-output/plan.json --start-frame 20 --end-frame 40 --output demo-output/motion.mp4
python -m unittest discover -s tests -v
```

Review the complete preview and silent motion sample. After actual approval, the agent sets the plan's approval to approved and runs the render command. An example can be marked automatic for an isolated automated test; this doesn't grant automatic mode to a user's project.

See [timeline format and commands](.agents/skills/video-edit/references/timeline.md), [release validation](docs/release-validation.md), and [behavioral evaluation cases](evals/cases.json).

## Privacy and rights

The bundled scripts use local media and make no API/upload calls. The host model still processes the material supplied to its tools; this is not a claim that the entire AI conversation runs offline. Additional external uploads require a specific user choice. Real captures must preserve the truth of the scene and be sanitized before packaging. Fonts, music and supplied assets retain their own licenses; MIT covers this repository's original instructions and code.

## Contributing

Keep shared constraints in SKILL.md and conditional guidance in references. Add scripts when they make a repeated operation deterministic. Reproduce a media bug with a small synthetic fixture, run the existing tests, and describe the actual exported behavior and limitations. Keep the compatibility page honest; a configured CI matrix isn't a passed CI run. Submit changes through a pull request; publishing/tagging is the maintainer's decision.

License: [MIT](LICENSE).
