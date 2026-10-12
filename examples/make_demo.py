"""Create an entirely synthetic demo, with no private/third-party media."""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".agents" / "skills" / "video-edit" / "scripts"))
from media import ffmpeg, run, write_json
from PIL import Image, ImageDraw


def find_font():
    paths = ["/System/Library/Fonts/Supplemental/Arial.ttf", "C:/Windows/Fonts/arial.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]
    return next((str(Path(p)) for p in paths if Path(p).is_file()), None)


def make_demo(folder, font=None):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    master = folder / "synthetic-master.mp4"
    if master.exists():
        raise ValueError("Demo source exists; choose a new folder")
    run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
         "-f", "lavfi", "-i", "testsrc2=size=320x480:rate=24:duration=2",
         "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=2",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ac", "2",
         "-map_metadata", "-1", "-t", "2", str(master)])
    image = Image.new("RGB", (560, 400), "#e8edf4")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 540, 90), fill="#29354b")
    draw.text((40, 42), "SYNTHETIC DEMO / NOT A REAL PRODUCT", fill="white")
    draw.rectangle((30, 120, 270, 350), fill="#bcc9dc")
    draw.rectangle((290, 120, 530, 350), fill="#c7ddce")
    draw.text((50, 145), "Illustration A", fill="#182334")
    draw.text((310, 145), "Illustration B", fill="#182334")
    image.save(folder / "synthetic-screen.png")
    font = font or find_font()
    if not font:
        raise ValueError("No local demo font found; use --font with an installed TTF")
    plan = {
        "master": "synthetic-master.mp4", "canvas": {"width": 320, "height": 480, "fps": 24},
        "mode": "guided", "approval": "pending", "background": {"color": "#181b23"},
        "safe_box": [10, 10, 300, 460],
        "caption_style": {"font": str(Path(font).resolve()), "size": 18, "direction": "auto",
                          "color": "#ffffff", "background": "#29354b", "padding": 8},
        "scenes": [
            {"start_frame": 0, "end_frame": 24, "face_box": [16, 16, 128, 128], "face_shape": "circle",
             "spoken_text": "Synthetic tone, no real narration.",
             "media": {"path": "synthetic-screen.png", "type": "image", "box": [20, 160, 280, 220]}},
            {"start_frame": 24, "end_frame": 48, "face_box": [170, 18, 128, 128], "face_shape": "circle",
             "transition_frames": 12, "spoken_text": "Synthetic tone, no real narration.",
             "media": {"path": "synthetic-screen.png", "type": "image", "box": [20, 160, 280, 220]}}
        ],
        "captions": [
            {"start_frame": 0, "end_frame": 24, "text": "سلام دنیا · Test 123", "box": [12, 396, 296, 70]},
            {"start_frame": 24, "end_frame": 48, "text": "پیش‌نمایش آزمایشی", "box": [12, 396, 296, 70]}
        ],
    }
    write_json(folder / "plan.json", plan)
    write_json(folder / "cuts.json", {
        "canvas": {"width": 320, "height": 480, "fps": 24}, "master_locked": False,
        "cuts": [{"source": "synthetic-master.mp4", "in": 0, "out": 1, "speed": 1},
                 {"source": "synthetic-master.mp4", "in": 1, "out": 2, "speed": 1.25}]
    })
    write_json(folder / "project.json", {
        "version": 1, "title": "Synthetic engine demo", "stage": "preview",
        "package_files": ["project.json", "plan.json", "cuts.json",
                          "synthetic-master.mp4", "synthetic-screen.png"],
        "asset_notice": "Generated test patterns, drawing, and tone. No real product/person.",
        "font_notice": "Installed font; not included for redistribution."
    })
    return folder


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder")
    parser.add_argument("--font")
    args = parser.parse_args()
    print(make_demo(args.folder, args.font))
