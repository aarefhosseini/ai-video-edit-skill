---
name: video-edit
description: Create or edit short videos and companion covers, captions, and carousels from footage, recordings, references, and brand inputs. Use for take selection, screen-recorded demos, color and audio cleanup, framing, subtitles, motion, and reviewable video production. Excludes long-form production, publishing, and account management.
---

# Video Edit

Turn a creator's intent and real assets into a clean, intentional edit with fewer revision cycles. Support Persian/RTL and English; use the user's language. Work through the host agent's available tools and local media utilities. No separate paid API, account, proprietary editor, or Codevo branding is required.

## Start with the actual brief

Before production, establish what the user wants to make, for whom, and where it will appear. Reuse answers already given. Read [references/intake.md](references/intake.md) and ask only the missing questions that affect this project, in one concise batch. Accept a provided video or reference as a starting point; don't require a full brand kit.

Ask the user to choose **guided** (approve the complete preview before final rendering) or **automatic** (execute within the agreed brief and report consequential choices). A request for automatic execution authorizes ordinary local production within that brief, not publishing, paid services, account changes, or fabricating evidence.

Inspect files before planning around them. Run `scripts/media.py doctor`, then `inspect` for each media source. Adapt command paths to this skill's actual location. The agent performs setup, commands, and corrections; don't hand terminal chores to a nontechnical creator. See [references/runtime.md](references/runtime.md) for environment discovery, agent-led setup, capability fallbacks, and portability.

## Keep one project record

Create a new project folder outside the installed skill. Use `assets/project-template.json` as a starting point and fill it from evidence, not imagined values. Maintain:

- `project.json`: brief, mode, destination, brand, source paths, selected master, edit permissions, missing assets, decisions, and current stage.
- `plan.json`: frame-based timeline with take choices, spoken text, supporting visual, crop/layout, captions, and transitions.
- `references.md`: inspected references, exact URLs, observation scope/date, relevant choices, visible metrics and uncertainty.

Make paths relative to the project where possible. Keep originals intact. Record a source fingerprint and derive timing from inspected media. Locking a master preserves its speech, cuts, speed, retouch, and audio unless the user explicitly changes that contract. A previous project's frame count, font, mask shape, or speed is never a universal default.

## Research and creative direction

For a new concept, find and inspect relevant examples using available search/browser tools, considering the user's references first. Read [references/research.md](references/research.md). Explain specific opportunities to improve the hook, visual proof, clarity, pacing, and ending. Support claims of success with actual observable metrics and date; separate aesthetic relevance from demonstrated performance. Optimize for attention and comprehension; never promise virality.

If video/audio cannot be accessed, state what was inspected and use the available evidence. Ask for an accessible reference when essential; otherwise proceed with a declared creative proposal. A thumbnail or caption isn't evidence of timing or sound design.

## Build the edit

Read [references/editing.md](references/editing.md) for take selection, audio, color, retouch, captions, framing, and motion. Read [references/capture.md](references/capture.md) when screen footage is needed. Use the host's real browser/screen-recording capabilities when available; capture the exact relevant action, not an unrelated tour. Read [references/delivery.md](references/delivery.md) for covers, carousels, captions, and post-publication analysis.

Use AI judgment to compare takes and design the narrative; use deterministic code for cuts, frame positions, timestamps, and exports. Use native host image/video generation only when available, included in the user's selected environment, and appropriate to the brief. Do not introduce separate paid APIs. Generated decoration or explanatory illustration may replace missing decoration; it cannot prove a real transaction, product feature, customer result, or event. Preserve identity and spoken meaning. Cloning a voice or replacing a face requires an explicit request for that specific operation.

For every scene, connect the spoken claim to an actual supporting visual or mark it as narration/illustration. Flag uncertain transcription, names, numbers, and inconsistencies for focused review. If an essential asset is missing, request it once. If the user declines, create a fitting illustrative alternative, restructure around available real footage, or deliver a clearly described partial preview. Never silently call an incomplete result complete.

The bundled `media.py assemble` handles explicit cut lists, resizing, frame-rate normalization, speed adjustments, and optional audio/color cleanup. `composite.py` handles approved frame-based face/media layouts, source crops, captions, backgrounds, simple transitions, contact sheets, and H.264 export. Read [references/timeline.md](references/timeline.md) when using these engines. They are starting engines, not limits on creative direction. Extend a project-local renderer when the agreed design needs unsupported motion, masking, sound mixing, or another export format. Never mutate the installed skill to customize one job.

## Preview and approval

In guided mode, provide **every section** in timeline order with its spoken text, real asset, precise region, face/media size and position, caption styling, and start/end state. Include short motion samples of proposed transitions. A script or a handful of attractive frames is insufficient. `composite.py preview` creates an exhaustive scene/caption contact-sheet set; add motion samples for transitions before requesting approval.

Prepare concrete reviewable previews first, then wait for explicit approval of that preview before final rendering. Do not ask again after the same preview is approved. Material design changes need a revised preview. In automatic mode, render within the agreed constraints without inventing additional approval steps. At either mode's completion, don't publish or send messages to others.

## Verify and deliver

Read [references/quality.md](references/quality.md). Perform technical checks, full visual review, and audio/meaning checks appropriate to the edit. `media.py verify` decodes all frames, checks timestamps, output dimensions/rate, and audio identity for locked masters. Technical success alone doesn't establish readable text, good pacing, accurate narration, or tasteful retouch. Explicitly identify any unavailable listening or native-platform review.

Deliver the chosen video export, optional SRT, cover/caption requested by the brief, and an editable code project with relative paths and assets. Package only the selected, sanitized assets with the user's redistribution rights; do not ship raw browser sessions, cookies, credentials, other people's personal data, or unrelated recordings. Call code-based projects what they are, not Premiere/CapCut projects.

Give a short report: what changed, why, what was checked, open limitations, and clickable output paths. Keep paid API usage at zero. Distinguish project completion from publication and observed performance. Update the project record so the next revision continues from the latest approved state.
