# Quality gates

Use checks that measure the output, not tests that match headings or repeat configuration text.

## Technical

- Inspect actual decoded frames, frame timestamps, rate, size, duration, orientation, pixel format and color metadata. Derive expectations from this project.
- Decode all video/audio; verify no errors. Flag whole-frame blackouts, but allow intentional black transitions when explicitly recorded in the plan.
- In locked-audio mode, compare compressed payloads, presentation times, decoded PCM, and sample count with the source. A container's last packet duration can differ after remux; report it separately. A matching filename or duration doesn't prove identity.
- For intentionally edited audio, confirm speech timing/meaning, clipping and transitions; do not demand byte identity with uncut raw footage.
- Inspect real exported captions and cover crops, not just text strings or source layouts.

## Content and craft

Review every scene and every caption; additionally inspect cut/transition boundaries and moving overlays. Check full audio when available. Verify that the highlighted source is the one the narration refers to; neither an illustration nor a test result is a real commercial outcome.

Read the important facts at the intended mobile display size. Check Persian/Latin joining and numerals with the actual font; some font/runtime combinations need a different shaping path. Look for cut words, unintended pauses, facial distortion, mask flicker, darkened skin, artificial audio, duplicate captions, and distracting motion.

Record platform overlay/crop assumptions. Prefer a native destination preview when available. A geometric safe-box model doesn't establish correctness in every app version/device or expanded-caption state. Ads and organic placements may have different constraints.

## Approval and completeness

Guided final exports require approval of the complete visual preview; automatic mode uses the user's agreed limits. A material change to an approved design isn't a silent correction. Missing essential scenes remain in the report. Stop calling an artifact final if its necessary content or checks remain unresolved.

Final note: actual file paths, selected version, changes/reasons, completed checks and remaining limitations. “Couldn't listen” or “native mobile preview not checked” is honest evidence, not an invitation to invent a successful check.
