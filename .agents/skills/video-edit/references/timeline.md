# Engine timeline format

The agent writes a project-specific plan. Frame intervals are half-open: start is included, end is excluded. Inspect source duration/rate first. Every scene must cover the contiguous selected master's timeline without overlap or gaps. Captions are ordered and nonoverlapping. Pixel boxes are [x, y, width, height]; source crops use source pixel coordinates. Original orientation must be normalized before compositing.

## Raw assembly

Use an explicit JSON file with canvas {width, height, fps}, master_locked false, and cuts [{source, in, out, speed}]. In/out are source seconds; speed defaults to 1. Optional color {brightness, contrast, saturation} and audio_cleanup {denoise, loudness} are applied only with the user's authorization. Assembly cuts and speed changes intentionally modify raw audio; compositing thereafter copies the selected master audio.

## Compositing

Required: master, canvas, mode (guided/automatic), approval (pending/approved), scenes. Scene fields: start_frame, end_frame, face_box, optional face_crop, face_shape (circle/rounded/rectangle), transition_frames, and media. The field face_box positions the master footage; its subject can be a person, an object, or any other base video. For a full-canvas video without a face inset, use a full-canvas rectangle. Media fields: path, type (video/image), box, optional crop, fit (contain/cover), source_in (seconds for video). Supporting videos must cover their scene; the engine doesn't silently loop or freeze a short recording.

Optional background {color, image}; safe_box for a reviewed project-specific placement assumption; captions [{start_frame, end_frame, text, box}] and caption_style {font, size, direction, color, background, padding, radius}. Caption direction is auto/rtl/ltr, default auto. Font is a local TTF/OTF or another format supported by installed Pillow. The engine chooses RAQM when present and falls back to Arabic reshaping plus bidi otherwise; review actual mixed-script output.

Optional intentional_black_frames is an explicit list of frame indices, not a blanket permission for blackouts. The selected master is read intact; no fresh speed/retouch/audio cleanup is added by the compositor.

## Commands

- media.py inspect FILE
- media.py assemble CUTS.json --output master.mp4
- composite.py preview PLAN.json --output review/revision-01
- composite.py motion PLAN.json --start-frame 0 --end-frame 45 --output motion-01.mp4
- composite.py render PLAN.json --output final.mp4
- media.py subtitles PLAN.json --output captions.srt
- media.py verify final.mp4 --master master.mp4 --expected expected.json --report review/technical.json
- media.py package project.json --output editable.zip

Paths resolve relative to the JSON file. Output won't overwrite a source; existing outputs require a new revision or explicit --force. Motion samples are silent and labeled as such. A final guided render requires approval approved. Automatic mode is selected by the user, not silently by the renderer.

Examples/make_demo.py in the repository generates an entirely synthetic, reproducible fixture and a valid plan for learning/testing. Its generated footage is explicitly illustration/test material, never evidence of a real product.
