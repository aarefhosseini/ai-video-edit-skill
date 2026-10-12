# Editorial and visual decisions

## Takes and narrative

Transcribe with timestamps when an audio tool is available. Compare repeated takes by meaning/completeness, clarity, natural delivery, gaze, facial expression, focus, clipping, and compatibility with adjacent shots. Give the reason for a choice. A user's exact take selection wins. “Last complete take” is an optional tie-breaker, not a universal instruction.

Cut false starts and repetition when permitted, preserving breaths, word endings, and natural rhythm. Check both sides of every cut. Fastest isn't automatically best; keep a visual long enough to understand the fact. Adjust pacing around information changes rather than random zooms. Preserve the exact selected ending/CTA.

For locked masters, no recutting, additional speed, color/retouch pass, or audio processing unless explicitly reopened. Use the master's timeline for all supporting visuals.

## Audio

Inspect codec, sample rate, clipping, noise, and source timing. Use conservative noise cleanup when permitted; compare before/after for metallic speech and lost consonants. Preserve pitch during approved speed changes and keep processing to one master pass. Normalize for the actual destination/brief, not a fixed platform loudness promise. Music/SFX are optional, licensed/provided, and subordinate to intelligibility. Check full speech audibly when the tools allow it; replay uncertain edits individually.

## Color and retouch

Determine orientation and HDR/SDR/color state before filtering. `media.py assemble` blocks known HDR transfer inputs rather than applying an unreviewed SDR conversion. Create a project-local deliberate tone-mapping pass and compare representative frames if needed.

Use balanced exposure, white balance, contrast, and skin tone before creative grading. Don't apply a whole-frame blur as skin retouch. Use a tracked feathered skin-only mask and protect eyes, glasses, eyebrows, lips, beard/hair, and background. Compare expression and texture over motion, not a single still. Preserve facial geometry and identity. Apply retouch once; don't stack it again on a selected retouched master.

## Framing

Choose the focus per scene: face, action, number, interface detail, or environment. The same full-page crop won't work for a pricing figure and a homepage tour. Use real source crops and enough scale for mobile reading. Keep face/captions away from the active detail. Maintain spatial continuity for repeated UI/face positions; justified changes should feel intentional.

The bundled compositor supports pixel boxes, source crops, contain/cover fitting, circle/rounded face masks, a supplied background, and time-based face movement. Its fixed canvas coordinates are project inputs. For dynamic tracking, shadows, refraction, custom motion paths, multiple simultaneous clips, or audio mixing, extend the **project-local** renderer and validate it. Do not claim those features are built-in controls.

## Captions and graphics

Use actual speech; mark uncertain names, numbers, and technical vocabulary for focused review. Never replace “credit” with “cash” because the script expected it. Condensed captions may remove filler while preserving meaning; record whether they are verbatim or condensed.

Break text by meaning and available reading time, not a rigid word count. Check Persian joining, RTL, punctuation, mixed Latin words, numerals, and line wrapping using the actual output font. Use brand inputs if present; otherwise choose restrained styling. A logo isn't a reason to encase the entire video in a promotional frame.

Each motion/graphic should direct attention, explain a relation, or connect scenes. Preview continuity at cuts and transition boundaries. Avoid double face overlays, restarting the animated background on each scene, or hiding a key word during an entrance. Match sound events only when that audio is actually available and selected.
