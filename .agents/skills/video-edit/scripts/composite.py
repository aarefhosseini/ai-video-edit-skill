"""Frame-based local compositor with honest source/audio preservation."""
from __future__ import annotations

import argparse
from functools import lru_cache
import html
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

import av
from PIL import Image, ImageDraw, ImageFont, ImageOps, features

from media import (canvas_settings, check_output, ffmpeg, finite_number, inspect,
                   local_path, read_json, verify, video_stream, write_json)


def smooth(value):
    value = min(1, max(0, value))
    return value * value * value * (value * (value * 6 - 15) + 10)


def box(value, name, canvas=None):
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(f"{name} requires [x, y, width, height]")
    for item in value:
        finite_number(item, name, 0)
    x, y, width, height = value
    if width <= 0 or height <= 0:
        raise ValueError(f"{name} requires positive size")
    if canvas and (x + width > canvas[0] + 0.01 or y + height > canvas[1] + 0.01):
        raise ValueError(f"{name} extends outside the canvas")
    return value


class Reader:
    """Monotonic timestamp reader; reset only for a backward preview seek."""
    def __init__(self, path):
        self.path = path
        self.container = None
        self.reset()

    def reset(self):
        if self.container:
            self.container.close()
        self.container = av.open(str(self.path))
        self.stream = self.container.streams.video[0]
        self.iterator = iter(self.container.decode(self.stream))
        self.current, self.next, self.last_requested = None, None, -1
        self.offset, self.index = None, 0
        self.advance()

    def advance(self):
        try:
            frame = next(self.iterator)
        except StopIteration:
            self.next = None
            return
        now = float(frame.time) if frame.time is not None else self.index / float(self.stream.average_rate)
        if self.offset is None:
            self.offset = now
        self.next = (now - self.offset, frame.to_image().convert("RGB"))
        self.index += 1

    def at(self, seconds):
        if seconds < self.last_requested - 1e-6:
            self.reset()
        while self.next is not None and self.next[0] <= seconds + 1e-6:
            self.current = self.next
            self.advance()
        self.last_requested = seconds
        if self.current is None:
            if self.next is None:
                raise ValueError(f"No decodable frames: {self.path}")
            return self.next[1].copy()
        return self.current[1].copy()

    def close(self):
        self.container.close()


class Project:
    def __init__(self, plan_path):
        self.path = Path(plan_path).resolve()
        self.root = self.path.parent
        self.data = read_json(self.path)
        self.width, self.height, self.fps = canvas_settings(self.data)
        self.master = local_path(self.root, self.data["master"])
        self.info = inspect(self.master)
        stream = video_stream(self.info)
        if not stream:
            raise ValueError("Master has no video")
        if abs(self.info["rotation_degrees"]) > 0.1:
            raise ValueError("Normalize source orientation before using the compositor")
        if stream["color_transfer"] in (16, 18):
            raise ValueError("HDR master requires a reviewed tone-map pass before RGB compositing")
        duration = stream["duration"] or self.info["duration"]
        self.frames = round(duration * self.fps)
        self.duration = self.frames / self.fps
        self.scenes = self.data.get("scenes", [])
        self.captions = self.data.get("captions", [])
        self.readers = {}
        self.images = {}
        self.font_path = None
        if self.captions:
            self.font_path = local_path(self.root, self.data["caption_style"]["font"])
        previous = 0
        for scene in self.scenes:
            start, end = scene.get("start_frame"), scene.get("end_frame")
            if type(start) is not int or type(end) is not int or start != previous or end <= start or end > self.frames:
                raise ValueError("Scenes must form a contiguous, nonoverlapping frame timeline")
            previous = end
            box(scene["face_box"], "face_box", (self.width, self.height))
            if scene.get("face_shape", "rounded") not in ("rounded", "circle", "rectangle"):
                raise ValueError("Unknown face_shape")
            if scene.get("face_shape") == "circle" and scene["face_box"][2] != scene["face_box"][3]:
                raise ValueError("Circular face_box must be square")
            if scene.get("face_crop"):
                box(scene["face_crop"], "face_crop", (stream["width"], stream["height"]))
            if scene.get("media"):
                media = scene["media"]
                source = local_path(self.root, media["path"])
                media["resolved"] = source
                box(media["box"], "media box", (self.width, self.height))
                if media.get("type", "video") not in ("video", "image"):
                    raise ValueError("media type must be video or image")
                if media.get("fit", "contain") not in ("contain", "cover"):
                    raise ValueError("media fit must be contain or cover")
                if media.get("type", "video") == "video":
                    metadata = inspect(source)
                    media_stream = video_stream(metadata)
                    if not media_stream or abs(metadata["rotation_degrees"]) > 0.1:
                        raise ValueError("Media requires upright video; normalize orientation first")
                    if media_stream["color_transfer"] in (16, 18):
                        raise ValueError("HDR supporting media requires deliberate tone mapping")
                    offset = finite_number(media.get("source_in", 0), "media source_in", 0)
                    required = offset + (end - start) / self.fps
                    if required > (media_stream["duration"] or metadata["duration"] or 0) + 1 / self.fps:
                        raise ValueError("Supporting video is too short; choose a shorter scene or a real still")
                    if media.get("crop"):
                        box(media["crop"], "media crop", (media_stream["width"], media_stream["height"]))
                else:
                    with Image.open(source) as im:
                        if media.get("crop"):
                            box(media["crop"], "media crop", im.size)
        if not self.scenes or previous != self.frames:
            raise ValueError(f"Scenes must cover all {self.frames} frames")
        previous_caption_end = 0
        for caption in self.captions:
            start, end = caption.get("start_frame"), caption.get("end_frame")
            if type(start) is not int or type(end) is not int or start < previous_caption_end or end <= start or end > self.frames:
                raise ValueError("Captions must be ordered, nonoverlapping, and inside the master")
            if not isinstance(caption.get("text"), str) or not caption["text"].strip():
                raise ValueError("Caption text is required")
            previous_caption_end = end
            box(caption["box"], "caption box", (self.width, self.height))
        self.background = self.data.get("background", {"color": "#181b23"})
        if self.background.get("image"):
            self.background_image = ImageOps.fit(
                self.image(local_path(self.root, self.background["image"])),
                (self.width, self.height), method=Image.Resampling.LANCZOS)
        else:
            self.background_image = None
        self.safe = self.data.get("safe_box")
        if self.safe:
            box(self.safe, "safe_box", (self.width, self.height))
        for scene in self.scenes:
            transition = scene.get("transition_frames", 0)
            if type(transition) is not int or transition < 0:
                raise ValueError("transition_frames must be a nonnegative integer")
            if transition > scene["end_frame"] - scene["start_frame"]:
                raise ValueError("Transition exceeds scene length")

    def image(self, path):
        if path not in self.images:
            with Image.open(path) as im:
                self.images[path] = ImageOps.exif_transpose(im).convert("RGB").copy()
        return self.images[path].copy()

    def reader(self, path):
        if path not in self.readers:
            self.readers[path] = Reader(path)
        return self.readers[path]

    def scene_index(self, frame):
        for index, scene in enumerate(self.scenes):
            if scene["start_frame"] <= frame < scene["end_frame"]:
                return index
        raise ValueError("Frame outside the timeline")

    @staticmethod
    def crop(image, bounds):
        if bounds:
            x, y, width, height = bounds
            return image.crop((round(x), round(y), round(x + width), round(y + height)))
        return image

    def face_box(self, frame, scene_index):
        scene = self.scenes[scene_index]
        target = scene["face_box"]
        transition = scene.get("transition_frames", 0)
        if scene_index and transition and frame - scene["start_frame"] < transition:
            previous = self.scenes[scene_index - 1]["face_box"]
            progress = smooth((frame - scene["start_frame"] + 1) / transition)
            return [a + (b - a) * progress for a, b in zip(previous, target)]
        return target

    @staticmethod
    def paste(canvas, image, bounds, shape="rectangle", fit="cover"):
        x, y, width, height = [round(v) for v in bounds]
        if fit == "contain":
            content = ImageOps.contain(image, (width, height), Image.Resampling.LANCZOS)
            tile = Image.new("RGB", (width, height), "#101116")
            tile.paste(content, ((width - content.width) // 2, (height - content.height) // 2))
        else:
            tile = ImageOps.fit(image, (width, height), Image.Resampling.LANCZOS)
        mask = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(mask)
        if shape == "circle":
            draw.ellipse((0, 0, width - 1, height - 1), fill=255)
        elif shape == "rounded":
            draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=min(width, height) * 0.06, fill=255)
        else:
            draw.rectangle((0, 0, width, height), fill=255)
        canvas.paste(tile, (x, y), mask)

    @lru_cache(maxsize=256)
    def caption_tile(self, text, width, height):
        style = self.data["caption_style"]
        size = style.get("size", 40)
        if type(size) is not int or size < 8:
            raise ValueError("Caption font size must be an integer >= 8")
        font = ImageFont.truetype(str(self.font_path), size)
        rtl = style.get("direction", "auto") == "rtl" or (
            style.get("direction", "auto") == "auto" and any("\u0600" <= char <= "\u06ff" for char in text))
        raqm = features.check_feature("raqm")
        kwargs = {"direction": "rtl" if rtl else "ltr"} if raqm else {}

        def shaped(value):
            if rtl and not raqm:
                import arabic_reshaper
                from bidi.algorithm import get_display
                return get_display(arabic_reshaper.reshape(value))
            return value

        padding = style.get("padding", 16)
        if type(padding) is not int or padding < 0:
            raise ValueError("Caption padding must be a nonnegative integer")
        lines = []
        for paragraph in text.split("\n"):
            current = ""
            for word in paragraph.split():
                trial = (current + " " + word).strip()
                if font.getlength(shaped(trial), **kwargs) > width - padding * 2:
                    if not current:
                        raise ValueError("A caption word doesn't fit; widen the box or adjust typography")
                    lines.append(current)
                    current = word
                    if font.getlength(shaped(word), **kwargs) > width - padding * 2:
                        raise ValueError("A caption word doesn't fit")
                else:
                    current = trial
            lines.append(current)
        ascent, descent = font.getmetrics()
        line_height = math.ceil((ascent + descent) * 1.05)
        needed = padding * 2 + line_height * len(lines)
        if needed > height:
            raise ValueError(f"Caption overflows vertically ({needed} > {height}); revise layout")
        tile = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(tile)
        background = style.get("background", "#141824")
        draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=style.get("radius", 16),
                               fill=background)
        top = (height - needed) / 2 + padding
        for index, line in enumerate(lines):
            draw.text((width / 2, top + index * line_height), shaped(line), font=font,
                      anchor="mt", fill=style.get("color", "#ffffff"), **kwargs)
        return tile

    def compose(self, frame):
        index = self.scene_index(frame)
        scene = self.scenes[index]
        canvas = self.background_image.copy() if self.background_image else Image.new(
            "RGB", (self.width, self.height), self.background.get("color", "#181b23"))
        media = scene.get("media")
        if media:
            path = media["resolved"]
            if media.get("type", "video") == "image":
                image = self.image(path)
            else:
                image = self.reader(path).at(media.get("source_in", 0) + (frame - scene["start_frame"]) / self.fps)
            image = self.crop(image, media.get("crop"))
            self.paste(canvas, image, media["box"], "rounded", media.get("fit", "contain"))
        face_image = self.reader(self.master).at(frame / self.fps)
        face_image = self.crop(face_image, scene.get("face_crop"))
        self.paste(canvas, face_image, self.face_box(frame, index), scene.get("face_shape", "rounded"))
        for caption in self.captions:
            if caption["start_frame"] <= frame < caption["end_frame"]:
                x, y, width, height = [round(v) for v in caption["box"]]
                tile = self.caption_tile(caption["text"], width, height)
                canvas.paste(tile, (x, y), tile)
        return canvas

    def geometry(self):
        issues = []
        if self.safe:
            sx, sy, sw, sh = self.safe
            for frame in range(self.frames):
                index = self.scene_index(frame)
                bounds = [("face", self.face_box(frame, index))]
                media = self.scenes[index].get("media")
                if media:
                    bounds.append(("media", media["box"]))
                bounds += [("caption", c["box"]) for c in self.captions
                           if c["start_frame"] <= frame < c["end_frame"]]
                for name, (x, y, width, height) in bounds:
                    if x < sx or y < sy or x + width > sx + sw or y + height > sy + sh:
                        issues.append({"frame": frame, "element": name})
        return {"frames_checked": self.frames, "safe_box": self.safe, "violations": issues,
                "passed": not issues, "native_platform_test": False}

    def close(self):
        for reader in self.readers.values():
            reader.close()


def preview(project, output):
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Preview directory exists and is not empty; choose a new revision")
    output.mkdir(parents=True, exist_ok=True)
    selected = {0, project.frames - 1}
    for scene in project.scenes:
        start, end = scene["start_frame"], scene["end_frame"]
        selected.update((start, (start + end - 1) // 2, end - 1))
        if start:
            selected.add(start - 1)
        transition = scene.get("transition_frames", 0)
        if transition:
            selected.add(min(end - 1, start + transition - 1))
    for caption in project.captions:
        selected.update((caption["start_frame"], caption["end_frame"] - 1))
    thumbs, rows = [], []
    for frame in sorted(selected):
        image = project.compose(frame)
        name = f"frame-{frame:06d}.jpg"
        image.save(output / name, quality=94)
        thumbnail = image.copy()
        thumbnail.thumbnail((216, 384))
        thumbs.append((frame, thumbnail))
        rows.append(f'<figure><img src="{name}" alt="Frame {frame}"><figcaption>'
                    f'{frame / project.fps:.3f}s · frame {frame}</figcaption></figure>')
    for page, start in enumerate(range(0, len(thumbs), 20)):
        sheet = Image.new("RGB", (1080, 4 * 408), "#dddddd")
        draw = ImageDraw.Draw(sheet)
        for index, (frame, image) in enumerate(thumbs[start:start + 20]):
            x, y = (index % 5) * 216, (index // 5) * 408
            sheet.paste(image, (x, y + 24))
            draw.text((x + 5, y + 5), f"{frame / project.fps:.3f}s", fill="#111111")
        sheet.save(output / f"contact-{page + 1}.jpg", quality=93)
    body = '<!doctype html><meta charset="utf-8"><title>Complete edit preview</title>' \
           '<style>body{font:16px system-ui;background:#12151d;color:white;padding:24px}' \
           'main{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}' \
           'figure{margin:0}img{width:100%;height:auto}figcaption{padding:8px}</style>' \
           '<h1>Complete edit preview</h1><p>All scenes, captions, and transition boundaries. ' \
           'Review motion samples and the spoken-text plan separately.</p><main>' + "".join(rows) + "</main>"
    (output / "index.html").write_text(body, encoding="utf-8")
    report = {"scene_count": len(project.scenes), "caption_count": len(project.captions),
              "sampled_frames": sorted(selected), "motion_samples_included": False,
              "geometry": project.geometry(), "approval": "pending"}
    write_json(output / "preview.json", report)
    return {"output": str(output), "samples": len(selected), "geometry_passed": report["geometry"]["passed"]}


def render(project, output, force=False, frame_range=None):
    inputs = [project.master]
    inputs += [s["media"]["resolved"] for s in project.scenes if s.get("media")]
    if project.background.get("image"):
        inputs.append(local_path(project.root, project.background["image"]))
    if project.font_path:
        inputs.append(project.font_path)
    output = check_output(output, inputs, force)
    if output.suffix.lower() != ".mp4":
        raise ValueError("Render output must be .mp4")
    audio_streams = [s for s in project.info["streams"] if s["type"] == "audio"]
    if audio_streams and audio_streams[0]["codec"] not in ("aac", "mp3", "alac"):
        raise ValueError("MP4 cannot preserve this audio codec; normalize an approved master or use a project-local MKV export")
    start, end = frame_range or (0, project.frames)
    if not 0 <= start < end <= project.frames:
        raise ValueError("Invalid motion sample frame range")
    if not frame_range:
        if project.data.get("mode", "guided") == "guided" and project.data.get("approval") != "approved":
            raise ValueError("Guided mode final render requires approval of the complete preview")
        if project.data.get("mode", "guided") not in ("guided", "automatic"):
            raise ValueError("mode must be guided or automatic")
        geometry = project.geometry()
        if not geometry["passed"]:
            raise ValueError("Project safe-box violations; revise or explicitly update the destination assumptions")
    with tempfile.TemporaryDirectory(prefix="video-composite-", dir=output.parent) as temp:
        temp = Path(temp)
        video = temp / "video.mp4"
        cmd = [ffmpeg(), "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
               "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{project.width}x{project.height}",
               "-framerate", str(project.fps), "-i", "pipe:0", "-frames:v", str(end - start),
               "-c:v", "libx264", "-preset", "fast", "-crf", "18",
               "-vf", "scale=in_range=full:out_range=limited:out_color_matrix=bt709,format=yuv420p",
               "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
               "-an", "-map_metadata", "-1", "-movflags", "+faststart", str(video)]
        with (temp / "render.log").open("wb") as log:
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=log)
            try:
                for frame in range(start, end):
                    process.stdin.write(project.compose(frame).tobytes())
                process.stdin.close()
                code = process.wait()
                if code:
                    raise RuntimeError((temp / "render.log").read_text(encoding="utf-8")[-6000:])
            except BaseException:
                if process.poll() is None:
                    process.terminate()
                process.wait()
                raise
        final = temp / "final.mp4"
        if frame_range:
            # Motion-only samples intentionally omit sound and are labeled as such.
            video.replace(final)
        else:
            cmd = [ffmpeg(), "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                   "-i", str(video), "-i", str(project.master), "-map", "0:v:0", "-map", "1:a:0?",
                   "-c", "copy", "-map_metadata", "-1", "-map_chapters", "-1", "-movflags", "+faststart", str(final)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stderr[-6000:])
        report = verify(final, {"width": project.width, "height": project.height, "fps": project.fps,
                               "frames": end - start}, master=None if frame_range else project.master,
                        allow_black=bool(project.data.get("intentional_black_frames")))
        allowed_black = set(project.data.get("intentional_black_frames", []))
        unexpected_black = [f for f in report["black_frames"] if f + start not in allowed_black]
        if unexpected_black:
            report["issues"].append("Black frames outside explicit planned intervals")
            report["passed"] = False
        if not report["passed"]:
            raise RuntimeError(f"Output verification failed: {report['issues']}")
        final.replace(output)
    report.update(output=str(output), motion_sample_silent=bool(frame_range),
                  source_sha256=project.info["sha256"])
    write_json(output.with_suffix(".verification.json"), report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preview", "render", "motion"))
    parser.add_argument("plan")
    parser.add_argument("--output", required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--start-frame", type=int)
    parser.add_argument("--end-frame", type=int)
    args = parser.parse_args()
    project = None
    try:
        project = Project(args.plan)
        if args.command == "preview":
            result = preview(project, args.output)
        else:
            frames = None
            if args.command == "motion":
                if args.start_frame is None or args.end_frame is None:
                    raise ValueError("Motion sample requires --start-frame and --end-frame")
                frames = (args.start_frame, args.end_frame)
            result = render(project, args.output, args.force, frames)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, RuntimeError, OSError, KeyError, ImportError, av.FFmpegError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    finally:
        if project:
            project.close()


if __name__ == "__main__":
    sys.exit(main())
