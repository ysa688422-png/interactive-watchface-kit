#!/usr/bin/env python3
"""Create a portable n67 project using original, replaceable geometric artwork."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import secrets
import shutil
import tempfile

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SIZE = (336, 480)
ART_SIZE = (336, 432)


def flower(draw, center, radius, color=(242, 240, 255, 255)):
    x, y = center
    for n in range(5):
        a = n * math.tau / 5 - math.pi / 2
        px, py = x + math.cos(a) * radius * .65, y + math.sin(a) * radius * .65
        r = radius * .55
        draw.ellipse((px-r, py-r, px+r, py+r), fill=color)
    r = radius * .24
    draw.ellipse((x-r, y-r, x+r, y+r), fill=(235, 195, 92, 255))


def avatar(name):
    im = Image.new("RGBA", ART_SIZE)
    d = ImageDraw.Draw(im)
    powered = name == "bomb"
    color = (80, 63, 122, 255) if not powered else (232, 173, 73, 255)
    if powered:
        points = []
        for n in range(20):
            a = n * math.pi / 10 - math.pi / 2
            r = 115 if n % 2 == 0 else 72
            points.append((168 + math.cos(a) * r, 246 + math.sin(a) * r))
        d.polygon(points, fill=color)
        d.ellipse((111, 190, 225, 304), fill=(67, 48, 100, 255))
        flower(d, (168, 246), 42)
        return im
    d.rounded_rectangle((112, 229, 224, 378), radius=45, fill=color)
    d.ellipse((108, 131, 228, 251), fill=(181, 160, 213, 255))
    d.arc((108, 131, 228, 251), 186, 353, fill=color, width=14)
    closed = name.endswith("closed")
    for x in (145, 191):
        if closed:
            d.arc((x-9, 182, x+9, 194), 0, 180, fill=color, width=3)
        else:
            d.ellipse((x-4, 183, x+4, 195), fill=(58, 54, 88, 255))
    if "smile" in name:
        d.arc((156, 204, 180, 220), 0, 180, fill=color, width=3)
    else:
        d.line((159, 212, 177, 212), fill=color, width=3)
    stage = {
        "pull-start": .15, "pull-1": .30, "pull-bridge": .45,
        "pull-mid": .60, "pull-finish": .8, "pull-2": 1.0,
    }.get(name, 0)
    left_hand = (85 + int(stage*35), 312 - int(stage*80))
    d.line(((121, 253), (86, 276), left_hand), fill=color, width=17)
    d.line(((215, 254), (244, 286), (226, 329)), fill=color, width=17)
    d.ellipse((left_hand[0]-9, left_hand[1]-9, left_hand[0]+9, left_hand[1]+9),
              fill=(181, 160, 213, 255))
    d.line(((141, 363), (135, 410)), fill=color, width=15)
    d.line(((195, 363), (201, 410)), fill=color, width=15)
    if name == "human-flower":
        d.line((169, 322, 169, 262), fill=(90, 124, 112, 255), width=3)
        flower(d, (169, 260), 17)
        d.line(((120, 264), (150, 319), (169, 309)), fill=color, width=15)
    return im


def gradient():
    im = Image.new("RGBA", SIZE)
    d = ImageDraw.Draw(im)
    for y in range(SIZE[1]):
        t = y / (SIZE[1]-1)
        rgb = tuple(round(a*(1-t)+b*t) for a, b in zip((239, 233, 247), (193, 171, 218)))
        d.line((0, y, 336, y), fill=(*rgb, 255))
    return im


def effect(name):
    im = Image.new("RGBA", ART_SIZE)
    d = ImageDraw.Draw(im)
    if name == "smoke":
        d.rectangle((0, 0, *ART_SIZE), fill=(63, 47, 80, 255))
        for x, y, r in [(45, 160, 100), (245, 225, 140), (140, 350, 120)]:
            d.ellipse((x-r, y-r, x+r, y+r), fill=(88, 69, 107, 255))
    elif name == "flash":
        d.ellipse((-80, -90, 420, 410), fill=(255, 239, 202, 240))
    else:
        phase = 0 if name.endswith("1") else .25
        for x, y, r in [(76, 146, 87), (268, 224, 100), (112, 339, 65)]:
            for n in range(18):
                a = n * math.tau / 18 + phase
                d.line((x+math.cos(a)*r*.3, y+math.sin(a)*r*.3,
                        x+math.cos(a)*r, y+math.sin(a)*r),
                       fill=(238, 193, 95, 220), width=2)
    return im


def icon(name):
    im = Image.new("RGBA", (22, 22))
    d = ImageDraw.Draw(im)
    c = "#FFFFFF" if name.endswith("dark") else "#34233F"
    if "heart" in name:
        d.ellipse((2, 3, 12, 13), fill=c)
        d.ellipse((10, 3, 20, 13), fill=c)
        d.polygon(((2, 9), (20, 9), (11, 20)), fill=c)
    else:
        d.ellipse((3, 7, 9, 18), fill=c)
        d.ellipse((12, 3, 18, 14), fill=c)
        d.ellipse((4, 2, 8, 6), fill=c)
        d.ellipse((13, 16, 17, 20), fill=c)
    return im


def digit(ch):
    im = Image.new("RGBA", (20 if ch == ":" else 30, 64), "black")
    d = ImageDraw.Draw(im)
    c = "#AEB3B8"
    if ch == ":":
        d.ellipse((8, 22, 12, 26), fill=c)
        d.ellipse((8, 39, 12, 43), fill=c)
    else:
        segments = ["abcedf", "bc", "abged", "abgcd", "fgbc", "afgcd",
                    "afgecd", "abc", "abcdefg", "abfgcd"][int(ch)]
        lines = {
            "a": (7, 10, 23, 10), "b": (25, 13, 25, 29),
            "c": (25, 35, 25, 51), "d": (7, 54, 23, 54),
            "e": (5, 35, 5, 51), "f": (5, 13, 5, 29), "g": (7, 32, 23, 32),
        }
        for segment in segments:
            d.line(lines[segment], fill=c, width=3)
    return im


def create(output, name, face_id, profile, threshold):
    if output.exists():
        raise ValueError("Output already exists; choose a new directory.")
    if not isinstance(profile, dict):
        raise ValueError("Profile must be a JSON object.")
    if profile.get("device") != "n67" or (profile.get("width"), profile.get("height")) != SIZE:
        raise ValueError("This native template only supports n67 / 336x480; other devices require an adapter.")
    if not re.fullmatch(r"[1-9][0-9]{8}", face_id):
        raise ValueError("The native face ID must be nine digits and not start with zero.")
    if not name.strip() or len(name.encode("utf8")) > 59 or "\0" in name:
        raise ValueError("Name must be nonempty and at most 59 UTF-8 bytes without NUL.")
    if type(threshold) is not int or not 1 <= threshold <= 999:
        raise ValueError("Heart-rate threshold must be an integer in 1..999.")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Build in a sibling temporary directory so errors leave no partial project.
    with tempfile.TemporaryDirectory(prefix=".watchface-", dir=output.parent) as temp:
        p = Path(temp) / "project"
        images = p / "images/_lua/watchface"
        aod = p / "images_aod"
        images.mkdir(parents=True)
        aod.mkdir()
        definition = json.loads((ROOT / "templates/xiaomi-n67/wfDef.json").read_text(encoding="utf-8"))
        definition.update(name=name, id=face_id)
        geometry = {}
        for resource in definition["elementsNormal"][0]["jsImgList"]:
            key = Path(resource).stem
            xy = (0, 0)
            if key == "background-lavender":
                im = gradient()
            elif key.startswith(("human-", "pull-")) or key == "bomb":
                im = avatar(key)
            elif key in ("smoke", "flash", "fireworks-1", "fireworks-2"):
                im = effect(key)
            elif key.startswith("footer-"):
                im = Image.new("RGBA", (336, 65), (0, 0, 0, 0))
                xy = (0, 415)
            elif key.startswith("icon-"):
                im = icon(key)
                xy = (89, 455) if "steps" in key else (256, 455)
            elif key == "ui-background-shade":
                im = Image.new("RGBA", ART_SIZE)
                ImageDraw.Draw(im).rectangle((0, 0, 336, 100), fill=(0, 0, 0, 100))
            else:
                raise ValueError(f"Unsupported template resource: {key}")
            im.save(images / f"{key}.png")
            geometry[key] = {"x": xy[0], "y": xy[1], "w": im.width, "h": im.height}
        lua = (ROOT / "templates/xiaomi-n67/main.lua").read_text(encoding="utf-8")
        lines = ['local assetGeometry = {'] + [
            f'    ["{key}"] = {{ x = {g["x"]}, y = {g["y"]} }},'
            for key, g in geometry.items()
        ] + ['} -- ASSET_GEOMETRY']
        lua = lua.replace("local assetGeometry = {} -- ASSET_GEOMETRY", "\n".join(lines))
        lua = lua.replace("local HEART_RATE_THRESHOLD = 120", f"local HEART_RATE_THRESHOLD = {threshold}")
        (images / "main.lua").write_text(lua, encoding="utf-8")
        base = Image.new("RGBA", SIZE, "black")
        d = ImageDraw.Draw(base)
        d.line((168, 213, 168, 316), fill=(70, 85, 80, 255), width=3)
        flower(d, (168, 201), 45, (173, 174, 185, 255))
        base.save(aod / "aod-background.png")
        for ch in "0123456789:":
            key = "aod-colon" if ch == ":" else f"aod-digit-{ch}"
            digit(ch).save(aod / f"{key}.png")
        preview = gradient()
        preview.alpha_composite(avatar("human-neutral-open"))
        preview.convert("RGB").resize((230, 328), Image.Resampling.LANCZOS).save(p / "images/preview.png")
        (p / "wfDef.json").write_text(json.dumps(definition, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        (p / "asset-geometry.json").write_text(json.dumps(geometry, indent=2)+"\n", encoding="utf-8")
        settings = dict(profile)
        settings["heart_rate_threshold"] = threshold
        (p / "profile.json").write_text(json.dumps(settings, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        (p / "ARTWORK.txt").write_text(
            "Original geometric example artwork generated by create_project.py (MIT).\n"
            "Replace PNGs with artwork you may use. Keep alpha and asset-geometry.json\n"
            "coordinates aligned with main.lua. The preview is not a firmware test.\n", encoding="utf-8"
        )
        p.rename(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", type=Path, default=ROOT/"profiles/xiaomi-band-9-pro.json")
    parser.add_argument("--name", default="Interactive Bloom")
    parser.add_argument("--id", default=None)
    parser.add_argument("--threshold", type=int)
    args = parser.parse_args()
    try:
        profile = json.loads(args.profile.read_text(encoding="utf-8"))
        if not isinstance(profile, dict):
            raise ValueError("Profile must be a JSON object.")
        threshold = args.threshold if args.threshold is not None else profile.get("heart_rate_threshold", 120)
        create(args.output.resolve(), args.name,
               args.id or str(secrets.randbelow(900000000)+100000000), profile, threshold)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Cannot create project: {exc}\n")
    print(json.dumps({"project": str(args.output.resolve()), "device": "n67",
                      "threshold": threshold, "hardware_tested": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
