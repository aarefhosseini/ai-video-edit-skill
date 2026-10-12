# Runtime and capabilities

The skill runs in Codex/Claude Code; the scripts run on the user's machine. The skill itself does not grant browser, recording, audio, image-generation, network, or shell capabilities. Discover what is actually exposed before promising an operation.

## Agent-led preparation

- Locate an available Python 3.12–3.13 runtime; the pinned rendering stack requires Python 3.12 or later. The scripts use portable Python/Path APIs and no shell-string execution.
- Run `python scripts/media.py doctor`. The doctor uses the standard library and can report missing dependencies.
- If needed and allowed by the host, create a **project-local** `.venv` and install `scripts/requirements.txt` into it. Use the venv Python directly; activation isn't required. Choose `bin/python` on macOS/Linux and `Scripts/python.exe` on Windows.
- The default requirements include a locally executable FFmpeg bundled by `imageio-ffmpeg`. An existing `FFMPEG` path or PATH binary can be used. Do not download random executables or change global packages/PATH.
- Downloads may be needed for the packages or a selected local speech model. Report that preparation honestly; offline inference doesn't mean an unprepared computer can install without internet. Handle host sandbox/permission prompts through the host's normal mechanism.
- The creator should provide files and preferences, not commands. Show one concise actionable blocker if preparation cannot be completed.

## Capabilities and fallback

| Capability | Preferred path | Fallback |
|---|---|---|
| Search/reference inspection | Host search and browser | Supplied accessible references; declared proposal |
| Real screen recording | Host recording or permitted browser capture | Ask for a recording; labeled screenshot motion for static content |
| Transcription | Available local Whisper tool/model | Host audio capability; supplied transcript plus uncertain spans |
| Audio review | Actual listening or available audio analysis | Technical checks plus explicit unreviewed-audio limitation |
| Decoration generation | Included native host tool | Supplied assets or locally drawn shapes/graphics |
| Retouch/masking | Available local detector/tracker, project-local renderer | Conservative manual tracked region or preserve original |
| Render | Local Python/FFmpeg | Produce a usable edit plan/source package and report missing render capability |

Never say a video was heard/viewed because a transcript/contact sheet exists. Never silently replace a capability with a third-party paid API. Read a host's available tool documentation instead of prescribing Codex-specific tool identifiers to Claude or vice versa.

## Compatibility status

Target macOS, Windows, Linux and both agents. Record actual tested combinations in the repository's compatibility page; do not equate portable code or a configured CI matrix with an executed host end-to-end test. Hardware/OS/browser access and codec builds vary.
