#!/usr/bin/env python3
"""Export local, authorized artwork for the system Apple Watch Photos face.

No networking, device control, custom watchface code, or .watchface generation.
All artwork is contained without cropping visible pixels or stretching.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import warnings
from pathlib import Path

from PIL import Image, ImageColor, ImageOps

DEFAULT_PROFILE = Path(__file__).parent / "profiles/apple-watch-photo-generic.json"
APPLE_PHOTOS_GUIDE = "https://support.apple.com/zh-cn/guide/watch/apd501eb33b3/watchos"
MAX_PIXELS = 40_000_000
MAX_PHOTOS = 24
PROFILE_KEYS = {
    "width", "height", "top_safe_fraction", "bottom_safe_fraction",
    "padding_fraction", "background_top", "background_bottom",
    "trim_transparent", "watch_model", "watchos_version",
}
LAYOUT_KEYS = PROFILE_KEYS - {"watch_model", "watchos_version", "width", "height"}


def local_path(value: str, base: Path | None = None) -> Path:
    """Reject URLs; relative manifest paths resolve against the manifest."""
    if "://" in str(value) or str(value).lower().startswith(("data:", "file:")):
        raise ValueError("Only local filesystem images are accepted; URLs are unsupported.")
    path = Path(value).expanduser()
    if not path.is_absolute() and base is not None:
        path = base / path
    return path.resolve()


def read_rgba(path: Path) -> Image.Image:
    """Read one still image and apply orientation before layout."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as source:
            if source.width * source.height > MAX_PIXELS:
                raise ValueError(f"Image exceeds {MAX_PIXELS:,} pixels: {path.name}")
            if getattr(source, "n_frames", 1) != 1:
                raise ValueError(f"Use a still image, not an animation: {path.name}")
            return ImageOps.exif_transpose(source).convert("RGBA")


def integer(value, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer from {minimum} to {maximum}.")
    return value


def fraction(value, name: str, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{name} must be a number.")
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= maximum:
        raise ValueError(f"{name} must be from 0 to {maximum}.")
    return value


def validate_profile(profile: dict) -> dict:
    result = dict(profile)
    for key in ("width", "height"):
        result[key] = integer(result[key], key, 64, 4096)
    for key, limit in (
        ("top_safe_fraction", .8), ("bottom_safe_fraction", .8),
        ("padding_fraction", .45),
    ):
        result[key] = fraction(result[key], key, limit)
    if result["top_safe_fraction"] + result["bottom_safe_fraction"] >= .9:
        raise ValueError("Leave at least 10% of the canvas height for the artwork.")
    for key in ("background_top", "background_bottom"):
        rgb = ImageColor.getrgb(result[key])
        if len(rgb) != 3:
            raise ValueError(f"{key} must be an opaque RGB color.")
    if not isinstance(result["trim_transparent"], bool):
        raise ValueError("trim_transparent must be a boolean.")
    for key in ("watch_model", "watchos_version"):
        if not isinstance(result[key], str):
            raise ValueError(f"{key} must be text.")
    return result


def compose_layers(photo: dict, base: Path) -> Image.Image:
    """Reassemble local cropped layers, refusing any accidental clipping."""
    if "source" in photo:
        if "layers" in photo:
            raise ValueError("Use source or layers for each photo, not both.")
        return read_rgba(local_path(photo["source"], base))
    if not photo.get("layers"):
        raise ValueError("Each photo needs source, or canvas and non-empty layers.")
    canvas = photo.get("canvas", [])
    if not isinstance(canvas, list) or len(canvas) != 2:
        raise ValueError("A layer composition needs canvas: [width, height].")
    w, h = [integer(v, "canvas size", 1, 8192) for v in canvas]
    if w * h > MAX_PIXELS:
        raise ValueError("Composition canvas is too large.")
    result = Image.new("RGBA", (w, h))
    for layer in photo["layers"]:
        source = read_rgba(local_path(layer["file"], base))
        x = integer(layer.get("x", 0), "layer.x", 0, w)
        y = integer(layer.get("y", 0), "layer.y", 0, h)
        if x + source.width > w or y + source.height > h:
            raise ValueError(f"Layer would be clipped by canvas: {Path(layer['file']).name}")
        opacity = fraction(layer.get("opacity", 1), "layer.opacity", 1)
        if opacity != 1:
            source.putalpha(source.getchannel("A").point(lambda a: round(a * opacity)))
        result.alpha_composite(source, (x, y))
    return result


def gradient(size: tuple[int, int], top: str, bottom: str) -> Image.Image:
    w, h = size
    a, b = ImageColor.getrgb(top), ImageColor.getrgb(bottom)
    strip = Image.new("RGB", (1, h))
    strip.putdata([
        tuple(round(a[c] + (b[c] - a[c]) * y / max(1, h - 1)) for c in range(3))
        for y in range(h)
    ])
    return strip.resize((w, h)).convert("RGBA")


def render_photo(source: Image.Image, profile: dict) -> tuple[Image.Image, dict]:
    """Contain the entire source/alpha content below the clock reserve."""
    p = validate_profile(profile)
    source = source.convert("RGBA")
    original_size = list(source.size)
    alpha_bbox = source.getchannel("A").getbbox()
    if alpha_bbox is None:
        raise ValueError("Artwork is fully transparent.")
    source_box = alpha_bbox if p["trim_transparent"] else (0, 0, *source.size)
    source = source.crop(source_box)
    w, h = p["width"], p["height"]
    left = math.ceil(w * p["padding_fraction"])
    right = math.floor(w * (1 - p["padding_fraction"]))
    top = math.ceil(h * p["top_safe_fraction"])
    bottom = math.floor(h * (1 - p["bottom_safe_fraction"]))
    bw, bh = right - left, bottom - top
    scale = min(bw / source.width, bh / source.height)
    rw = max(1, min(bw, math.floor(source.width * scale)))
    rh = max(1, min(bh, math.floor(source.height * scale)))
    art = source.resize((rw, rh), Image.Resampling.LANCZOS)
    x, y = left + (bw - rw) // 2, top + (bh - rh) // 2
    out = gradient((w, h), p["background_top"], p["background_bottom"])
    out.alpha_composite(art, (x, y))
    report = {
        "source_size": original_size,
        "preserved_source_box": list(source_box),
        "artwork_box": [x, y, x + rw, y + rh],
        "available_box": [left, top, right, bottom],
        "scale": scale,
        "visible_pixels_cropped": False,
        "time_or_data_added_by_exporter": False,
        "note": "Only fully transparent outer margins may be removed. Source-internal crops cannot be repaired.",
    }
    # Export opaque RGB with no copied EXIF or personal source metadata.
    return out.convert("RGB"), report


def safe_name(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", name).strip(" .")
    return name[:90] or "photo"


def guide_text(profile: dict, filenames: list[str]) -> str:
    return f"""Apple Watch 照片简化版 · 导入说明

本目录是 {len(filenames)} 张静态 PNG，不是 Apple Watch 安装包。
画布 {profile['width']} × {profile['height']}；目标机型：{profile['watch_model']}；
watchOS：{profile['watchos_version']}。通用画布不是硬件原生分辨率。
本工具不添加时间、日期、步数或心率文字，时间由 Apple Watch 系统绘制。
请使用无旧表盘文字的原画；工具不会自动识别或清除原图已有的数据。

1. 把 PNG 保存到已配对 iPhone 的“照片”中，可用隔空投送或你常用的文件传输方式。
2. 打开 iPhone 的 Watch App → 表盘图库 → 照片 → 选取照片。
3. 先只选两张普通/持花图，或选择你喜欢的其他图片，然后轻点添加。
4. 在实际预览中调整照片缩放与时钟布局；上方约 {profile['top_safe_fraction']:.0%} 已留作时间区。
   若版本支持手动时间位置，优先放上方。不要继续放大照片，以免系统裁掉人物。
   苹果的自动构图、圆角和系统时间布局仍可能改变可见区域，须以手表预览为准。
5. 想让一张图固定显示，就只选这一张；多图时由系统照片表盘切换。

能做：显示静态原画；系统支持轻点屏幕/抬腕换照片。
不能做：自动眨眼、拔销动画、心率超过 120 自动变身、严格固定的两态切换、
        将某张白花图指定为单独的息屏界面。
黑底白花也只是一张普通照片。常亮显示是否支持及如何显示由机型、watchOS、
系统照片表盘和用户设置决定。本工具不会把小米 Lua、.bin 转成 Apple 原生表盘，
也不会生成或伪造 .watchface 文件。

请只使用自己拥有或得到相应许可的素材；代码许可不包含导入图像的权利。
原图已存在的裁切无法由排版工具补回。本工具只保证导出时不再裁掉可见内容。
本工具不连接手表；安装与真实显示尚需用户在自己的设备上确认。

官方使用说明（核验于 2026-10-20）：
{APPLE_PHOTOS_GUIDE}
"""


def export_photos(photos: list[dict], base: Path, profile: dict, output: Path,
                  overwrite: bool = False) -> dict:
    if not isinstance(photos, list) or not all(isinstance(photo, dict) for photo in photos):
        raise ValueError("photos must be a JSON array of photo objects.")
    if not 1 <= len(photos) <= MAX_PHOTOS:
        raise ValueError(f"Export between 1 and {MAX_PHOTOS} photos.")
    profile = validate_profile(profile)
    planned = []
    for i, photo in enumerate(photos, 1):
        name = safe_name(str(photo.get("name", f"photo-{i:02d}")))
        planned.append(f"{i:02d}-{name}.png")
    destinations = [output / name for name in planned] + [
        output / "使用说明.txt", output / "export-report.json",
    ]
    if not overwrite and any(path.exists() for path in destinations):
        raise ValueError("Output files already exist; choose a new directory or pass --overwrite.")
    # Validate and render all inputs before writing any files.
    rendered = []
    for filename, photo in zip(planned, photos):
        settings = {**profile, **{key: photo[key] for key in LAYOUT_KEYS if key in photo}}
        image, metrics = render_photo(compose_layers(photo, base), settings)
        rendered.append((filename, image, {**metrics, "settings": validate_profile(settings)}))
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "adapter": "apple-watch-photos", "capability": "static-photos-only",
        "official_guide": APPLE_PHOTOS_GUIDE,
        "profile": profile, "device_tested": False, "photos": [],
    }
    for filename, image, metrics in rendered:
        image.save(output / filename, "PNG", optimize=True)
        report["photos"].append({"file": filename, **metrics})
    (output / "使用说明.txt").write_text(guide_text(profile, planned), encoding="utf-8")
    (output / "export-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", nargs="+", help="Local still images you are authorized to use.")
    source.add_argument("--manifest", type=Path, help="JSON photos with local sources or layers.")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    for key in ("width", "height"):
        parser.add_argument("--" + key, type=int)
    for key in ("top_safe_fraction", "bottom_safe_fraction", "padding_fraction"):
        parser.add_argument("--" + key.replace("_", "-"), type=float)
    for key in ("background_top", "background_bottom", "watch_model", "watchos_version"):
        parser.add_argument("--" + key.replace("_", "-"))
    parser.add_argument("--trim-transparent", action=argparse.BooleanOptionalAction, default=None)
    return parser


def main(argv=None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    try:
        profile = json.loads(args.profile.read_text(encoding="utf-8"))
        profile.update({key: getattr(args, key) for key in PROFILE_KEYS
                        if getattr(args, key, None) is not None})
        if args.manifest:
            manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
            photos = manifest["photos"]
            base = args.manifest.resolve().parent
        else:
            photos = [{"source": str(local_path(p)), "name": Path(p).stem} for p in args.input]
            base = Path.cwd()
        report = export_photos(photos, base, profile, args.output, args.overwrite)
    except (OSError, ValueError, TypeError, KeyError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as error:
        parser.exit(2, f"Export failed: {error}\n")
    print(f"Exported {len(report['photos'])} static PNGs to {args.output}")
    print("Photos only: no blink, heart-rate transformation, or independent AOD.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
