import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

MODULE = Path(__file__).resolve().parents[1] / "export_photos.py"
spec = importlib.util.spec_from_file_location("export_photos", MODULE)
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)


class ExportTests(unittest.TestCase):
    def profile(self, **changes):
        p = json.loads(export.DEFAULT_PROFILE.read_text())
        return {**p, **changes}

    def test_contain_preserves_all_edges_and_clock_reserve(self):
        source = Image.new("RGBA", (120, 90), "#00FF00")
        for point, color in [
            ((0, 0), "#FF0000"), ((119, 0), "#0000FF"),
            ((0, 89), "#FFFF00"), ((119, 89), "#FF00FF"),
        ]:
            source.putpixel(point, export.ImageColor.getrgb(color) + (255,))
        result, report = export.render_photo(source, self.profile(
            width=200, height=200, top_safe_fraction=.3, bottom_safe_fraction=.1,
            padding_fraction=.2, background_top="#000000", background_bottom="#000000"))
        self.assertEqual(result.size, (200, 200))
        self.assertEqual(report["artwork_box"], [40, 75, 160, 165])
        for src, dest in [((0, 0), (40, 75)), ((119, 0), (159, 75)),
                          ((0, 89), (40, 164)), ((119, 89), (159, 164))]:
            self.assertEqual(result.getpixel(dest), source.getpixel(src)[:3])
        self.assertEqual(result.crop((0, 0, 200, 60)).getbbox(), None)

    def test_alpha_composition_does_not_double_apply_alpha(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            Image.new("RGBA", (4, 4), (0, 0, 255, 255)).save(base / "blue.png")
            Image.new("RGBA", (2, 2), (255, 0, 0, 128)).save(base / "red.png")
            composed = export.compose_layers({"canvas": [4, 4], "layers": [
                {"file": "blue.png"}, {"file": "red.png", "x": 1, "y": 1},
            ]}, base)
            self.assertEqual(composed.getpixel((1, 1)), (128, 0, 127, 255))
            self.assertEqual(composed.getpixel((0, 0)), (0, 0, 255, 255))
            with self.assertRaisesRegex(ValueError, "clipped"):
                export.compose_layers({"canvas": [4, 4], "layers": [
                    {"file": "red.png", "x": 3, "y": 3}]}, base)

    def test_trim_removes_only_transparent_margin(self):
        source = Image.new("RGBA", (90, 90))
        source.paste((3, 4, 5, 255), (20, 10, 70, 80))
        _, report = export.render_photo(source, self.profile())
        self.assertEqual(report["preserved_source_box"], [20, 10, 70, 80])
        self.assertFalse(report["visible_pixels_cropped"])

    def test_cli_profile_overrides_and_private_paths_not_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            Image.new("RGBA", (30, 40), "#ABCDEF").save(base / "private.png")
            args = ["--input", str(base / "private.png"), "--output", str(base / "out"),
                    "--width", "400", "--height", "500", "--watch-model", "test-model",
                    "--watchos-version", "unknown"]
            self.assertEqual(export.main(args), 0)
            report_text = (base / "out/export-report.json").read_text()
            report = json.loads(report_text)
            self.assertEqual(report["profile"]["watch_model"], "test-model")
            self.assertNotIn(str(base), report_text)
            with Image.open(base / "out/01-private.png") as image:
                self.assertEqual(image.size, (400, 500))
                self.assertEqual(image.mode, "RGB")
            with self.assertRaises(SystemExit):
                export.main(args)  # refuses overwriting existing output

    def test_invalid_input_is_rejected(self):
        with self.assertRaises(ValueError):
            export.local_path("https://example.com/art.png")
        with self.assertRaises(ValueError):
            export.validate_profile(self.profile(top_safe_fraction=.7, bottom_safe_fraction=.4))
        with self.assertRaises(ValueError):
            export.render_photo(Image.new("RGBA", (30, 30)), self.profile())


if __name__ == "__main__":
    unittest.main()
