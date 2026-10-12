"""Local media helpers. No paid APIs, shell strings, or network calls."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fingerprint(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local_path(root, value):
    """Media inputs must be actual local files, never FFmpeg URL/protocol inputs."""
    if not isinstance(value, str) or not value:
        raise ValueError("Expected a nonempty local file path")
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = Path(root) / candidate
    candidate = candidate.resolve(strict=True)
    if not candidate.is_file():
        raise ValueError(f"Not a local file: {value}")
    return candidate


def ffmpeg():
    override = os.environ.get("FFMPEG")
    if override:
        found = shutil.which(override) or (override if Path(override).is_file() else None)
        if not found:
            raise RuntimeError("FFMPEG points to a missing executable")
        return str(Path(found).resolve())
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as exc:
        raise RuntimeError("FFmpeg unavailable. See references/runtime.md for agent-led setup.") from exc


def run(args, log=None):
    result = subprocess.run([str(x) for x in args], capture_output=True, text=True)
    if log:
        Path(log).write_text(result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(result.stderr[-6000:] or f"Command failed: {result.returncode}")
    return result


def doctor():
    packages = {}
    for name in ("av", "numpy", "Pillow", "arabic-reshaper", "python-bidi", "imageio-ffmpeg"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    try:
        binary = ffmpeg()
        version = run([binary, "-version"]).stdout.splitlines()[0]
    except RuntimeError as exc:
        binary, version = None, str(exc)
    return {
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "packages": packages,
        "ffmpeg": binary,
        "ffmpeg_version": version,
        "ready": bool(sys.version_info >= (3, 12) and binary and all(
            packages[name] for name in ("av", "numpy", "Pillow", "arabic-reshaper", "python-bidi"))),
        "paid_api_required": False,
        "browser_audio_and_generation": "Discover separately in the host agent",
    }


def inspect(path):
    import av
    path = Path(path).resolve(strict=True)
    streams = []
    with av.open(str(path)) as container:
        for stream in container.streams:
            record = {
                "type": stream.type,
                "codec": stream.codec_context.name,
                "duration": float(stream.duration * stream.time_base) if stream.duration is not None else None,
                "start_time": float(stream.start_time * stream.time_base) if stream.start_time is not None else None,
                "metadata": dict(stream.metadata),
            }
            if stream.type == "video":
                record.update(
                    width=stream.width, height=stream.height,
                    fps=float(stream.average_rate) if stream.average_rate else None,
                    pixel_format=stream.codec_context.format.name,
                    color_primaries=stream.codec_context.color_primaries,
                    color_transfer=stream.codec_context.color_trc,
                    colorspace=stream.codec_context.colorspace,
                    frames=stream.frames,
                )
            elif stream.type == "audio":
                record.update(sample_rate=stream.codec_context.sample_rate, channels=stream.codec_context.channels)
            streams.append(record)
        duration = container.duration / av.time_base if container.duration else None
    # FFmpeg exposes display-matrix rotation on builds where PyAV doesn't expose it.
    probe = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path)], capture_output=True, text=True)
    import re
    rotation_match = re.search(r"rotation of\s+([-+0-9.]+)\s+degrees", probe.stderr)
    rotation = float(rotation_match.group(1)) if rotation_match else 0
    return {
        "path": str(path), "bytes": path.stat().st_size, "sha256": fingerprint(path),
        "duration": duration, "streams": streams, "rotation_degrees": rotation,
    }


def video_stream(info):
    return next((s for s in info["streams"] if s["type"] == "video"), None)


def finite_number(value, name, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def canvas_settings(data):
    canvas = data.get("canvas", {})
    width, height, fps = canvas.get("width"), canvas.get("height"), canvas.get("fps")
    for value, name in ((width, "width"), (height, "height")):
        if type(value) is not int or value < 16 or value % 2:
            raise ValueError(f"canvas {name} must be an even integer >= 16")
    finite_number(fps, "fps", 1)
    if fps > 120:
        raise ValueError("fps must be <= 120")
    return width, height, fps


def check_output(path, inputs, force=False):
    path = Path(path).resolve()
    if path in {Path(p).resolve() for p in inputs}:
        raise ValueError("Output must not overwrite a source file")
    if path.exists() and not force:
        raise ValueError(f"Output exists; choose a new revision or use --force: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def assemble(plan_path, output, force=False):
    """Render an explicit raw-footage cut list. Frame counts derive from this plan."""
    plan_path = Path(plan_path).resolve()
    data = read_json(plan_path)
    if data.get("master_locked"):
        raise ValueError("Locked master: assembly/recutting is prohibited")
    width, height, fps = canvas_settings(data)
    cuts = data.get("cuts", [])
    if not cuts:
        raise ValueError("A cut list is required")
    sources = [local_path(plan_path.parent, c["source"]) for c in cuts]
    output = check_output(output, sources, force)
    if output.suffix.lower() != ".mp4":
        raise ValueError("Assembly output must be .mp4")
    binary = ffmpeg()
    expected_frames = 0
    reports = []
    source_infos = {}
    for source in set(sources):
        source_infos[source] = inspect(source)
        stream = video_stream(source_infos[source])
        if not stream:
            raise ValueError(f"No video stream: {source.name}")
        if stream["color_transfer"] in (16, 18):
            raise ValueError("HDR source requires a deliberate reviewed SDR/tone-map pass first")
    with tempfile.TemporaryDirectory(prefix="video-edit-", dir=output.parent) as temp:
        temp = Path(temp)
        parts = []
        for index, (cut, source) in enumerate(zip(cuts, sources)):
            start = finite_number(cut.get("in", 0), "cut in", 0)
            end = finite_number(cut["out"], "cut out", 0)
            speed = finite_number(cut.get("speed", 1), "cut speed", 0.25)
            if speed > 4 or end <= start:
                raise ValueError("Cut requires out > in and 0.25 <= speed <= 4")
            if end > (source_infos[source]["duration"] or 0) + 0.02:
                raise ValueError(f"Cut {index} extends beyond its source")
            frames = round((end - start) / speed * fps)
            if frames < 1:
                raise ValueError("Cut contains no output frames")
            duration = frames / fps
            part = temp / f"part-{index:04d}.mkv"
            video_filter = (
                f"setpts=(PTS-STARTPTS)/{speed},"
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,"
                f"fps={fps},tpad=stop_mode=clone:stop_duration=0.2,"
                f"trim=end_frame={frames},setpts=N/({fps}*TB)"
            )
            grade = data.get("color", {})
            if grade:
                brightness = finite_number(grade.get("brightness", 0), "brightness")
                contrast = finite_number(grade.get("contrast", 1), "contrast", 0)
                saturation = finite_number(grade.get("saturation", 1), "saturation", 0)
                if not -0.2 <= brightness <= 0.2 or contrast > 2 or saturation > 2:
                    raise ValueError("Use conservative grade ranges or a deliberate project-local grade")
                video_filter += f",eq=brightness={brightness}:contrast={contrast}:saturation={saturation}"
            video_filter += ",format=yuv420p"
            has_audio = any(s["type"] == "audio" for s in source_infos[source]["streams"])
            cmd = [binary, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                   "-ss", str(start), "-t", str(end - start), "-i", str(source)]
            if not has_audio:
                cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
            remaining, tempos = speed, []
            while remaining > 2:
                tempos.append(2)
                remaining /= 2
            while remaining < 0.5:
                tempos.append(0.5)
                remaining /= 0.5
            tempos.append(remaining)
            audio_filter = ",".join(f"atempo={x}" for x in tempos)
            audio_filter += f",aresample=48000,apad,atrim=duration={duration},asetpts=N/SR/TB"
            cmd += ["-map", "0:v:0", "-map", "0:a:0" if has_audio else "1:a:0",
                    "-vf", video_filter, "-af", audio_filter, "-frames:v", str(frames),
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-c:a", "pcm_s16le", "-ac", "2", "-t", str(duration),
                    "-map_metadata", "-1", "-map_chapters", "-1", str(part)]
            run(cmd, temp / f"part-{index:04d}.log")
            parts.append(part)
            expected_frames += frames
            reports.append({"source": str(source), "in": start, "out": end, "speed": speed, "frames": frames})
        # Only internally generated filenames enter the concat list.
        listing = temp / "concat.txt"
        listing.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
        final = temp / "master.mp4"
        cmd = [binary, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
               "-f", "concat", "-safe", "1", "-i", str(listing), "-map", "0:v:0", "-map", "0:a:0",
               "-vf", f"setpts=N/({fps}*TB),fps={fps},format=yuv420p",
               "-frames:v", str(expected_frames), "-c:v", "libx264", "-preset", "fast", "-crf", "18",
               "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
        audio = data.get("audio_cleanup", {})
        filters = []
        if audio.get("denoise"):
            filters += ["highpass=f=65", "afftdn=nf=-35:nr=4"]
        if "loudness" in audio:
            target = finite_number(audio["loudness"], "loudness")
            if not -24 <= target <= -12:
                raise ValueError("Loudness target must be between -24 and -12 LUFS")
            filters.append(f"loudnorm=I={target}:TP=-2:LRA=11")
        if filters:
            cmd += ["-af", ",".join(filters)]
        cmd += ["-map_metadata", "-1", "-map_chapters", "-1", "-movflags", "+faststart", str(final)]
        run(cmd)
        validation = verify(final, expected={"width": width, "height": height, "fps": fps, "frames": expected_frames},
                            allow_black=True)
        if not validation["passed"]:
            raise RuntimeError(f"Assembly verification failed: {validation['issues']}")
        final.replace(output)
    report = {"output": str(output), "frames": expected_frames, "duration": expected_frames / fps,
              "cuts": reports, "source_fingerprints": {str(p): i["sha256"] for p, i in source_infos.items()},
              "audio_intentionally_edited": True, "passed": True}
    write_json(output.with_suffix(".assembly.json"), report)
    return report


def audio_signature(path):
    import av
    compressed, pcm, times = hashlib.sha256(), hashlib.sha256(), hashlib.sha256()
    packets, samples, last_duration = 0, 0, None
    with av.open(str(path)) as container:
        stream = next(iter(container.streams.audio), None)
        if stream is None:
            return None
        for packet in container.demux(stream):
            if packet.size:
                compressed.update(bytes(packet))
                rational = packet.pts * stream.time_base if packet.pts is not None else None
                times.update((str(rational) + "\n").encode())
                packets += 1
                last_duration = packet.duration
    with av.open(str(path)) as container:
        for frame in container.decode(audio=0):
            # Include all channels exactly; the decoder's sample format is unchanged.
            pcm.update(frame.to_ndarray().tobytes())
            samples += frame.samples
    return {"payload_sha256": compressed.hexdigest(), "pts_sha256": times.hexdigest(),
            "pcm_sha256": pcm.hexdigest(), "packets": packets, "samples_per_channel": samples,
            "last_packet_duration": last_duration}


def verify(path, expected=None, master=None, allow_black=False):
    import av
    import numpy as np
    info = inspect(path)
    expected = expected or {}
    issues, black, timestamps, frames = [], [], [], 0
    stream = video_stream(info)
    if stream is None:
        raise ValueError("No video stream")
    fps = stream["fps"]
    for field in ("width", "height", "fps"):
        if field in expected and abs(stream[field] - expected[field]) > 0.001:
            issues.append(f"{field}: got {stream[field]}, expected {expected[field]}")
    try:
        with av.open(str(path)) as container:
            offset = None
            previous = None
            for frame in container.decode(video=0):
                now = float(frame.time) if frame.time is not None else None
                if now is None or (previous is not None and now <= previous):
                    timestamps.append(frames)
                if offset is None:
                    offset = now or 0
                if now is not None and fps and abs(now - offset - frames / fps) > max(0.001, 0.05 / fps):
                    timestamps.append(frames)
                previous = now
                pixels = frame.to_ndarray(format="gray")
                if float(pixels.mean()) < 3 and float(np.percentile(pixels, 99)) < 5:
                    black.append(frames)
                frames += 1
    except av.FFmpegError as exc:
        issues.append(f"Video decode error: {exc}")
    if timestamps:
        issues.append("Nonuniform or missing frame timestamps")
    if black and not allow_black:
        issues.append("Unexpected whole-frame blackouts")
    if "frames" in expected and frames != expected["frames"]:
        issues.append(f"Frame count {frames} != {expected['frames']}")
    duration = frames / fps if fps else None
    if "duration" in expected and (duration is None or abs(duration - expected["duration"]) > 1 / fps + 1e-6):
        issues.append("Decoded duration differs from project expectation")
    output_audio = audio_signature(path)
    source_audio = audio_signature(master) if master else None
    identity = None
    if master:
        if source_audio is None or output_audio is None:
            identity = source_audio is None and output_audio is None
        else:
            keys = ("payload_sha256", "pts_sha256", "pcm_sha256", "packets", "samples_per_channel")
            identity = all(source_audio[k] == output_audio[k] for k in keys)
        if not identity:
            issues.append("Locked source audio changed")
    return {
        "passed": not issues, "issues": issues, "frames": frames, "duration": duration,
        "width": stream["width"], "height": stream["height"], "fps": fps,
        "black_frames": black, "timestamp_error_frames": sorted(set(timestamps)),
        "source_audio": source_audio, "output_audio": output_audio, "audio_preserved": identity,
        "audio_review": "Technical decode/identity only; audible review is separate",
        "native_platform_review": False,
    }


def package(project_path, output, force=False):
    project_path = Path(project_path).resolve()
    root = project_path.parent
    data = read_json(project_path)
    entries = data.get("package_files", [])
    if not entries:
        raise ValueError("project.json must contain an explicitly reviewed package_files allowlist")
    files = []
    forbidden = {".git", ".venv", "__pycache__", "node_modules", "sessions", "cookies"}
    for value in entries:
        original = Path(value)
        if original.is_absolute() or ".." in original.parts or forbidden.intersection(original.parts):
            raise ValueError(f"Unsafe package entry: {value}")
        path = local_path(root, value)
        if not path.is_relative_to(root):
            raise ValueError(f"Package path escapes project: {value}")
        if any(p.is_symlink() for p in [root / original, *(root / original).parents] if p != root.parent):
            raise ValueError(f"Symlinked package input: {value}")
        files.append((value.replace("\\", "/"), path))
    output = check_output(output, [p for _, p in files], force)
    if output.suffix.lower() != ".zip":
        raise ValueError("Package output must be .zip")
    manifest = {"files": [{"path": name, "sha256": fingerprint(path), "bytes": path.stat().st_size}
                          for name, path in files], "requires_human_semantic_privacy_review": True}
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        archive = Path(temp) / "package.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
            for name, path in files:
                handle.write(path, arcname=name)
            handle.writestr("package-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        with zipfile.ZipFile(archive) as handle:
            bad = handle.testzip()
            if bad:
                raise RuntimeError(f"ZIP checksum failure: {bad}")
        archive.replace(output)
    return {"output": str(output), "files": len(files), "sha256": fingerprint(output)}


def subtitles(plan_path, output, force=False):
    plan_path = Path(plan_path).resolve()
    plan = read_json(plan_path)
    _, _, fps = canvas_settings(plan)
    output = check_output(output, [plan_path], force)
    if output.suffix.lower() != ".srt":
        raise ValueError("Subtitle output must be .srt")
    def stamp(frame):
        milliseconds = round(frame / fps * 1000)
        seconds, millis = divmod(milliseconds, 1000)
        minutes, sec = divmod(seconds, 60)
        hours, minute = divmod(minutes, 60)
        return f"{hours:02}:{minute:02}:{sec:02},{millis:03}"
    lines, previous = [], 0
    for index, caption in enumerate(plan.get("captions", []), 1):
        start, end = caption["start_frame"], caption["end_frame"]
        if type(start) is not int or type(end) is not int or start < previous or end <= start:
            raise ValueError("Invalid or overlapping subtitle frames")
        text = caption["text"].strip()
        if not text or "-->" in text:
            raise ValueError("Invalid subtitle text")
        lines += [str(index), f"{stamp(start)} --> {stamp(end)}", text, ""]
        previous = end
    if not lines:
        raise ValueError("No captions to export")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"output": str(output), "captions": len(lines) // 4}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    probe = commands.add_parser("inspect")
    probe.add_argument("file")
    assembly = commands.add_parser("assemble")
    assembly.add_argument("plan")
    assembly.add_argument("--output", required=True)
    assembly.add_argument("--force", action="store_true")
    qa = commands.add_parser("verify")
    qa.add_argument("file")
    qa.add_argument("--expected")
    qa.add_argument("--master")
    qa.add_argument("--allow-black", action="store_true")
    qa.add_argument("--report")
    bundle = commands.add_parser("package")
    bundle.add_argument("project")
    bundle.add_argument("--output", required=True)
    bundle.add_argument("--force", action="store_true")
    srt = commands.add_parser("subtitles")
    srt.add_argument("plan")
    srt.add_argument("--output", required=True)
    srt.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "doctor":
            result = doctor()
        elif args.command == "inspect":
            result = inspect(args.file)
        elif args.command == "assemble":
            result = assemble(args.plan, args.output, args.force)
        elif args.command == "verify":
            result = verify(args.file, read_json(args.expected) if args.expected else None,
                            args.master, args.allow_black)
            if args.report:
                write_json(args.report, result)
        elif args.command == "subtitles":
            result = subtitles(args.plan, args.output, args.force)
        else:
            result = package(args.project, args.output, args.force)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result.get("passed") is False or result.get("ready") is False:
            return 1
        return 0
    except (ValueError, RuntimeError, OSError, KeyError, ImportError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
