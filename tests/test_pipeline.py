"""Behavior tests against actual FFmpeg encodes, decodes, and exported assets."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".agents" / "skills" / "video-edit" / "scripts"))
sys.path.insert(0, str(ROOT / "examples"))
import media
from composite import Project, preview, render
from make_demo import make_demo


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="video-edit-tests-")
        cls.root = make_demo(Path(cls.temp.name) / "demo")
        cls.plan = media.read_json(cls.root / "plan.json")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def new_plan(self, name, mutate=None):
        data = copy.deepcopy(self.plan)
        if mutate:
            mutate(data)
        path = self.root / f"{name}.json"
        media.write_json(path, data)
        return path

    def test_inspect_actual_media(self):
        info = media.inspect(self.root / "synthetic-master.mp4")
        stream = media.video_stream(info)
        self.assertEqual((stream["width"], stream["height"], stream["fps"]), (320, 480, 24))
        self.assertAlmostEqual(stream["duration"], 2, places=3)
        self.assertEqual(len(info["sha256"]), 64)

    def test_cut_list_changes_duration(self):
        output = self.root / "assembled.mp4"
        report = media.assemble(self.root / "cuts.json", output)
        self.assertEqual(report["frames"], 43)
        result = media.verify(output, {"width": 320, "height": 480, "fps": 24, "frames": 43})
        self.assertTrue(result["passed"], result)
        self.assertIsNotNone(result["output_audio"])

    def test_locked_master_cannot_be_recut(self):
        data = media.read_json(self.root / "cuts.json")
        data["master_locked"] = True
        path = self.root / "locked-cuts.json"
        media.write_json(path, data)
        with self.assertRaisesRegex(ValueError, "Locked"):
            media.assemble(path, self.root / "illegal-assembly.mp4")

    def test_source_cannot_be_overwritten(self):
        with self.assertRaisesRegex(ValueError, "source"):
            media.assemble(self.root / "cuts.json", self.root / "synthetic-master.mp4", True)

    def test_guided_final_waits_for_approval(self):
        project = Project(self.root / "plan.json")
        try:
            with self.assertRaisesRegex(ValueError, "approval"):
                render(project, self.root / "unapproved.mp4")
            self.assertFalse((self.root / "unapproved.mp4").exists())
        finally:
            project.close()

    def test_final_preserves_audio_payload_pts_pcm(self):
        path = self.new_plan("approved", lambda p: p.update(approval="approved"))
        project = Project(path)
        try:
            report = render(project, self.root / "final.mp4")
            self.assertTrue(report["passed"], report)
            self.assertTrue(report["audio_preserved"])
            self.assertEqual(report["frames"], 48)
        finally:
            project.close()

    def test_automatic_mode_has_no_extra_approval(self):
        path = self.new_plan("automatic", lambda p: p.update(mode="automatic"))
        project = Project(path)
        try:
            self.assertTrue(render(project, self.root / "automatic.mp4")["passed"])
        finally:
            project.close()

    def test_preview_covers_all_scenes_captions_transitions(self):
        project = Project(self.root / "plan.json")
        try:
            preview(project, self.root / "review")
        finally:
            project.close()
        report = media.read_json(self.root / "review" / "preview.json")
        self.assertEqual(report["scene_count"], 2)
        self.assertEqual(report["caption_count"], 2)
        self.assertTrue({0, 23, 24, 35, 47}.issubset(report["sampled_frames"]))
        self.assertTrue((self.root / "review" / "index.html").is_file())
        self.assertEqual(report["approval"], "pending")

    def test_mask_screen_and_caption_are_rendered(self):
        project = Project(self.root / "plan.json")
        try:
            frame = project.compose(0)
            self.assertEqual(frame.getpixel((16, 16)), (24, 27, 35))
            self.assertNotEqual(frame.getpixel((80, 80)), (24, 27, 35))
            self.assertNotEqual(frame.getpixel((160, 270)), (24, 27, 35))
            self.assertNotEqual(frame.getpixel((160, 430)), (24, 27, 35))
        finally:
            project.close()

    def test_silent_motion_preview_before_approval(self):
        project = Project(self.root / "plan.json")
        try:
            report = render(project, self.root / "motion.mp4", frame_range=(20, 40))
            self.assertTrue(report["passed"])
            self.assertEqual(report["frames"], 20)
            self.assertIsNone(report["output_audio"])
        finally:
            project.close()

    def test_missing_shot_is_not_silently_substituted(self):
        path = self.new_plan("missing", lambda p: p["scenes"][0]["media"].update(path="missing.mp4", type="video"))
        with self.assertRaises(FileNotFoundError):
            Project(path)

    def test_short_recording_is_not_looped(self):
        path = self.new_plan("too-short", lambda p: p["scenes"][0]["media"].update(
            path="synthetic-master.mp4", type="video", source_in=1.5))
        with self.assertRaisesRegex(ValueError, "too short"):
            Project(path)

    def test_gap_is_rejected(self):
        path = self.new_plan("gap", lambda p: p["scenes"][1].update(start_frame=25))
        with self.assertRaisesRegex(ValueError, "contiguous"):
            Project(path)

    def test_actual_caption_font_overflow_is_rejected(self):
        path = self.new_plan("overflow", lambda p: p["caption_style"].update(size=100))
        project = Project(path)
        try:
            with self.assertRaisesRegex(ValueError, "fit|overflows"):
                project.compose(0)
        finally:
            project.close()

    def test_safe_box_checks_moving_frames(self):
        path = self.new_plan("unsafe", lambda p: p.update(safe_box=[10, 10, 200, 460]))
        project = Project(path)
        try:
            report = project.geometry()
            self.assertFalse(report["passed"])
            self.assertTrue(report["violations"])
        finally:
            project.close()

    def test_verify_rejects_wrong_expectations(self):
        result = media.verify(self.root / "synthetic-master.mp4", {"width": 1080, "frames": 2025})
        self.assertFalse(result["passed"])
        self.assertGreaterEqual(len(result["issues"]), 2)

    def test_srt_frame_rate_and_persian(self):
        result = media.subtitles(self.root / "plan.json", self.root / "captions.srt")
        text = (self.root / "captions.srt").read_text(encoding="utf-8")
        self.assertEqual(result["captions"], 2)
        self.assertIn("00:00:01,000 --> 00:00:02,000", text)
        self.assertIn("پیش‌نمایش آزمایشی", text)

    def test_package_only_allowlisted_files(self):
        (self.root / "private-note.txt").write_text("Must not be shipped", encoding="utf-8")
        output = self.root / "editable.zip"
        result = media.package(self.root / "project.json", output)
        with zipfile.ZipFile(output) as archive:
            self.assertNotIn("private-note.txt", archive.namelist())
            self.assertIsNone(archive.testzip())
            manifest = json.loads(archive.read("package-manifest.json"))
            self.assertEqual(len(manifest["files"]), result["files"])
        self.assertEqual(result["files"], 5)

    def test_package_rejects_escape_paths(self):
        path = self.root / "unsafe-package.json"
        media.write_json(path, {"package_files": ["../outside.txt"]})
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            media.package(path, self.root / "unsafe.zip")


if __name__ == "__main__":
    unittest.main()
