# Release validation — 0.1.0 beta

Checked on 2026-10-12. This report states executed checks separately from proposed ones.

## Executed

- Skill Creator quick_validate: valid name, frontmatter and skill structure.
- Python script compilation succeeded.
- 19 behavioral pipeline tests passed locally on macOS ARM64 with Python 3.12.13 and FFmpeg 7.1.
- Tests encoded and decoded actual generated clips. They covered cut-list duration, locked-master refusal, source preservation, guided approval, automatic rendering, unchanged audio payload/timestamps/PCM, every scene/caption preview, mask/layout output, silent motion samples, missing/short footage, malformed timelines, caption overflow, safe boxes, incorrect expectations, Persian SRT timing, allowlist packaging and path-escape rejection.
- Both agent installers copied canonical files without caches and refused replacement of an existing skill in isolated test directories.
- Synthetic preview contact sheet inspected: Persian joining and mixed Latin/numerals rendered, caption boxes fit, circular corners masked, face-layout transition remained inside the chosen geometry. This is a small engine fixture, not a demonstration of expert creative direction or real-person retouch.
- Additional private-source technical check: a full 67.5-second approved master was composited to a small 160×284 QA export at 30fps. All 2025 frames decoded with uniform timestamps and no blackouts; all 3165 audio payloads, presentation times, decoded PCM and 3239936 samples per channel matched the source. Private media and its QA export are not included in this public repository. The container's final audio packet duration differed by 28 samples while decoded content remained identical.
- Runtime doctor succeeded with an explicitly supplied FFmpeg executable, without requiring the optional executable-provider package to be installed. This checks existing-runtime discovery; a fresh dependency install remains a separate release check.

An assembly timing issue discovered by the cut-list test was corrected by deriving the final frame timestamps from the normalized frame sequence. Video assembly is re-encoded intentionally; subsequent locked-master compositing copies original audio without processing.

## Required before claiming stable broad support

1. Run the configured GitHub Actions jobs on Windows, Linux and macOS after publication. Verify initial dependency preparation in clean environments.
2. Run the installed skill end-to-end in both Codex and Claude Code. Evaluate actual behavior with the cases in evals/cases.json, including raw repeated speech takes, an approved master and missing evidence.
3. Have a creator outside the development conversation provide files and complete a project without terminal chores. Record questions, revisions, final artifacts and blockers.
4. Audibly review speech cuts, cleanup and speed changes on real creator footage; inspect retouch over motion and output captions at intended mobile size.
5. Review a final output in the actual target mobile app/placement where available. Geometry assumptions alone are not a universal platform guarantee.

The package is suitable for a public beta with these limits clearly stated. It has no executed Windows/Linux CI or independent creator trial yet. Publication and CI results are tracked on GitHub. No paid API call is part of the bundled media pipeline.
