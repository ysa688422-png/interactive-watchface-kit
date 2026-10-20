"""Exercise project creation invariants without any external compiler."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("creator", ROOT/"scripts/create_project.py")
creator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(creator)


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.target = Path(self.temp.name)/"new-project"
        self.profile = json.loads((ROOT/"profiles/xiaomi-band-9-pro.json").read_text())

    def test_complete_assets_and_native_aod(self):
        creator.create(self.target, "Example", "123456789", self.profile, 135)
        wf = json.loads((self.target/"wfDef.json").read_text())
        self.assertEqual(wf["headerFlags"], 4)
        self.assertEqual([e["align"] for e in wf["elementsAod"] if "align" in e], [1, 1])
        geometry = json.loads((self.target/"asset-geometry.json").read_text())
        for name in wf["elementsNormal"][0]["jsImgList"]:
            p = (self.target/"images"/name).with_suffix(".png")
            with Image.open(p) as im:
                g = geometry[p.stem]
                self.assertEqual((im.width, im.height), (g["w"], g["h"]))
                self.assertGreaterEqual(g["x"], 0)
                self.assertGreaterEqual(g["y"], 0)
                self.assertLessEqual(g["x"]+im.width, 336)
                self.assertLessEqual(g["y"]+im.height, 480)
        lua = (self.target/"images/_lua/watchface/main.lua").read_text()
        self.assertIn("local HEART_RATE_THRESHOLD = 135", lua)
        self.assertNotIn("> 120", lua)
        self.assertNotIn("<= 120", lua)

    def test_existing_project_is_not_overwritten(self):
        self.target.mkdir()
        sentinel = self.target/"keep.txt"
        sentinel.write_text("keep")
        with self.assertRaises(ValueError):
            creator.create(self.target, "Example", "123456789", self.profile, 120)
        self.assertEqual(sentinel.read_text(), "keep")

    def test_unknown_device_does_not_create_output(self):
        self.profile["width"] = 480
        with self.assertRaises(ValueError):
            creator.create(self.target, "Example", "123456789", self.profile, 120)
        self.assertFalse(self.target.exists())

    def test_invalid_profile_and_threshold_do_not_create_output(self):
        for value in (True, False, 120.5, "120", None, 0, 1000):
            with self.assertRaises(ValueError):
                creator.create(self.target, "Example", "123456789", self.profile, value)
            self.assertFalse(self.target.exists())
        with self.assertRaises(ValueError):
            creator.create(self.target, "Example", "123456789", [], 120)
        self.assertFalse(self.target.exists())

    def test_invalid_name_and_id_do_not_create_output(self):
        for name, face_id in [("x\0y", "123456789"), ("花"*30, "123456789"),
                              ("Example", "../unsafe"), ("Example", "012345678")]:
            with self.assertRaises(ValueError):
                creator.create(self.target, name, face_id, self.profile, 120)
            self.assertFalse(self.target.exists())


if __name__ == "__main__":
    unittest.main()
