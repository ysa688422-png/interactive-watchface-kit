#!/usr/bin/env python3
"""Locate a complete interactive-watchface-kit checkout without mutations."""

import argparse
import json
import os
from pathlib import Path
import sys


def is_kit_root(path):
    return (
        path.is_dir()
        and (path / "scripts").is_dir()
        and (path / "profiles").is_dir()
        and (
            (path / "templates" / "xiaomi-n67").is_dir()
            or (path / "apple-watch").is_dir()
        )
    )


def walk_ancestors(path):
    yield path
    yield from path.parents


def describe(root):
    known = {
        "create_project": "scripts/create_project.py",
        "validate_project": "scripts/validate_project.py",
        "pack_xiaomi": "scripts/pack_xiaomi.py",
        "xiaomi_profile": "profiles/xiaomi-band-9-pro.json",
        "xiaomi_template": "templates/xiaomi-n67",
        "apple_export": "apple-watch/export_photos.py",
        "apple_profile": "apple-watch/profiles/apple-watch-photo-generic.json",
    }
    return {
        "found": True,
        "root": str(root),
        "resources": {
            key: {"path": str(root / relative), "exists": (root / relative).exists()}
            for key, relative in known.items()
        },
        "note": "定位成功不代表打包依赖、设备兼容性或素材授权已经验证；先读取对应配置及工具说明。",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="Explicit complete repository root")
    args = parser.parse_args()
    configured = args.root or os.environ.get("WATCHFACE_KIT_ROOT")
    if configured:
        candidates = [Path(configured).expanduser().resolve()]
    else:
        skill_dir = Path(__file__).resolve().parent.parent
        candidates = list(walk_ancestors(skill_dir)) + list(walk_ancestors(Path.cwd()))
    seen = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if is_kit_root(candidate):
            print(json.dumps(describe(candidate), ensure_ascii=False, indent=2))
            return 0
    print(
        json.dumps(
            {
                "found": False,
                "reason": "未找到完整工程仓库。",
                "next_step": "提供完整 interactive-watchface-kit 目录并使用 --root，或设置 WATCHFACE_KIT_ROOT；仅安装技能不会附带原生编译器。",
                "explicit_root_checked": str(candidates[0]) if configured else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
