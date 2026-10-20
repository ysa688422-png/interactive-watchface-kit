"""Independent validation for this kit's single-Lua-face + native-AOD n67 profile.

This module does not import a packer, execute Lua, or certify firmware behavior.
Its checks deliberately cover a narrow, tested subset of the binary format.
"""
from __future__ import annotations

import hashlib
import json
import re
import struct
from pathlib import Path, PurePosixPath

from PIL import Image


class ValidationError(ValueError):
    """A project or package does not meet this kit's supported profile."""


def require(condition, message):
    if not condition:
        raise ValidationError(message)


WIDTH, HEIGHT = 336, 480
MAX_PACKAGE_BYTES = 64 * 1024 * 1024  # Validator safety limit, not a firmware limit.


def safe_path(root, name, *, must_exist=True):
    """Reject path traversal, absolute paths, Windows paths, and escaping symlinks."""
    require(isinstance(name, str) and bool(name), "Asset reference must be a nonempty string")
    require("\\" not in name and ":" not in name and not any(ord(c) < 32 for c in name),
            f"Unsafe asset reference: {name!r}")
    parts = name.split("/")
    require(not name.startswith("/") and all(p not in ("", ".", "..") for p in parts),
            f"Asset path must be relative without traversal: {name!r}")
    root = Path(root).resolve()
    target = root.joinpath(*PurePosixPath(name).parts).resolve()
    require(target.is_relative_to(root), f"Asset symlink escapes its directory: {name!r}")
    require(not must_exist or target.is_file(), f"Missing asset: {name}")
    return target


def png_path(folder, name):
    require(isinstance(name, str), "PNG name must be a string")
    reference = name if name.lower().endswith(".png") else name + ".png"
    return safe_path(folder, reference)


def png_pixels(path, *, preview=False):
    with Image.open(path) as image:
        require(image.format == "PNG", f"Expected PNG: {path.name}")
        w, h = image.size
        require(0 < w <= WIDTH and 0 < h <= HEIGHT, f"Image outside n67 dimensions: {path.name} {w}x{h}")
        require(not getattr(image, "is_animated", False), f"Animated PNG unsupported: {path.name}")
        if preview:
            require((w, h) == (230, 328), "Package preview must be 230x328")
        return (w, h), image.convert("RGBA").tobytes("raw", "BGRA")


def raw_lvgl(blob, label):
    require(len(blob) >= 4 and blob[0] in (4, 5), f"Unsupported Lua image format: {label}")
    flags = int.from_bytes(blob[1:4], "little")
    w, h = (flags >> 2) & 2047, flags >> 13
    require(0 < w <= WIDTH and 0 < h <= HEIGHT, f"Lua image dimensions out of bounds: {label}")
    require(len(blob) == 4 + w * h * 4, f"Incorrect Lua BGRA payload length: {label}")
    return (w, h), blob[4:]


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def integer(value, label, low=0, high=65535):
    require(type(value) is int and low <= value <= high, f"{label} must be an integer in {low}..{high}")
    return value


def rect(element, width, height, label):
    x = integer(element.get("x", 0), label + ".x", 0, WIDTH - 1)
    y = integer(element.get("y", 0), label + ".y", 0, HEIGHT - 1)
    require(x + width <= WIDTH and y + height <= HEIGHT,
            f"{label} exceeds 336x480: ({x}, {y}, {width}, {height})")
    return [x, y, width, height]


def validate_project(project, profile="n67"):
    require(profile == "n67", "Only the n67 profile is supported")
    project = Path(project).resolve()
    require(project.is_dir(), f"Project directory does not exist: {project}")
    definition_file = safe_path(project, "wfDef.json")
    definition = json.loads(definition_file.read_text("utf-8"), object_pairs_hook=no_duplicate_keys)
    require(isinstance(definition, dict), "wfDef.json must contain an object")
    if (project / "profile.json").exists():
        metadata = json.loads(safe_path(project, "profile.json").read_text("utf-8"),
                              object_pairs_hook=no_duplicate_keys)
        require(isinstance(metadata, dict) and metadata.get("device") == "n67" and
                metadata.get("width") == WIDTH and metadata.get("height") == HEIGHT,
                "profile.json must identify n67 at 336x480; relabeling a different device is unsupported")
        require(metadata.get("platform", "xiaomi-n67") == "xiaomi-n67",
                "profile.json is not a Xiaomi n67 platform")
    require(definition.get("headerFlags") == 4 and type(definition.get("headerFlags")) is int,
            "n67 normal+AOD requires explicit headerFlags=4 (0x1E is flags, not a style count)")
    require("faceStyleCount" not in definition, "Remove legacy faceStyleCount; use headerFlags=4")
    require(not definition.get("faces") and not definition.get("namedFaceRecords") and
            definition.get("faceLayout") != "named", "Named or multiple normal faces are unsupported")
    ident, name = str(definition.get("id", "")), definition.get("name")
    require(re.fullmatch(r"[0-9]{1,17}", ident) is not None, "id must contain 1..17 decimal digits")
    require(isinstance(name, str) and 0 < len(name.encode("utf-8")) <= 59 and "\0" not in name,
            "name must contain 1..59 UTF-8 bytes without NUL")
    for folder in ("images", "images_aod"):
        path = (project / folder).resolve()
        require(path.is_relative_to(project) and path.is_dir(), f"{folder} must be inside the project")
    images, aod_folder = project / "images", project / "images_aod"
    preview_path = png_path(images, definition.get("previewImg"))
    png_pixels(preview_path, preview=True)
    normal = definition.get("elementsNormal")
    require(isinstance(normal, list) and len(normal) == 1 and isinstance(normal[0], dict),
            "Exactly one ordinary Lua element is supported")
    entry = normal[0]
    require(entry.get("type") == "type_element_lua", "Ordinary element must be type_element_lua")
    rect(entry, 1, 1, "elementsNormal[0]")
    script = entry.get("jsFileName")
    require(isinstance(script, str) and script.endswith(".lua"), "jsFileName must reference a Lua file")
    lua_path = safe_path(images, script)
    lua_bytes = lua_path.read_bytes()
    require(0 < len(lua_bytes) <= 1024 * 1024, "Lua source must be nonempty and at most 1 MiB")
    require(not lua_bytes.startswith(b"\x1bLua"), "Supply plain Lua source, not Lua bytecode")
    lua_bytes.decode("utf-8")
    resources = entry.get("jsImgList")
    require(isinstance(resources, list) and 0 < len(resources) <= 512 and
            all(isinstance(item, str) for item in resources), "jsImgList must contain 1..512 image references")
    require(len(set(resources + [script])) == len(resources) + 1, "Duplicate Lua resource names")
    source_assets = {script: {"path": lua_path, "kind": "lua"}}
    total_pixels = 0
    for reference in resources:
        require(reference.endswith(".bin"), f"Lua images must use .bin references: {reference}")
        require(reference.isascii() and len(reference.encode("ascii")) <= 255,
                f"Lua resource name must be ASCII and at most 255 bytes: {reference}")
        binary = safe_path(images, reference, must_exist=False)
        if binary.is_file():
            blob = binary.read_bytes()
            size, pixels = raw_lvgl(blob, reference)
            source_assets[reference] = {"path": binary, "kind": "bin", "size": size}
        else:
            image = safe_path(images, str(PurePosixPath(reference).with_suffix(".png")))
            size, pixels = png_pixels(image)
            source_assets[reference] = {"path": image, "kind": "png", "size": size}
        total_pixels += len(pixels)
    require(script.isascii() and len(script.encode("ascii")) <= 255,
            "Lua resource name must be ASCII and at most 255 bytes")
    require(total_pixels < MAX_PACKAGE_BYTES, "Lua images exceed the validator's 64 MiB safety limit")
    geometry_count = 0
    if (project / "asset-geometry.json").exists():
        geometry = json.loads(safe_path(project, "asset-geometry.json").read_text("utf-8"),
                              object_pairs_hook=no_duplicate_keys)
        names = [PurePosixPath(item).stem for item in resources]
        require(isinstance(geometry, dict) and len(set(names)) == len(names) and
                set(geometry) == set(names), "asset-geometry.json must describe each ordinary image exactly once")
        for reference in resources:
            key = PurePosixPath(reference).stem
            item = geometry[key]
            require(isinstance(item, dict), f"Invalid image geometry: {key}")
            size = source_assets[reference]["size"]
            require([item.get("w"), item.get("h")] == list(size), f"Image geometry dimensions differ: {key}")
            rect(item, *size, "asset-geometry." + key)
            geometry_count += 1
    aod = definition.get("elementsAod")
    require(isinstance(aod, list) and 3 <= len(aod) <= 32, "AOD requires background and native hour/minute elements")
    require(not list(aod_folder.rglob("*.lua")), "AOD must not contain Lua or its own timers")
    clocks, rectangles = [], []
    for index, element in enumerate(aod):
        label = f"elementsAod[{index}]"
        require(isinstance(element, dict), f"{label} must be an object")
        kind = element.get("type")
        if kind == "element":
            size, _ = png_pixels(png_path(aod_folder, element.get("image")))
            rectangle = rect(element, *size, label)
        elif kind == "widge_dignum":
            source = element.get("dataSrc")
            require(source in ("0811", "1011"), f"{label} supports native hour 0811 or minute 1011 only")
            require(type(element.get("showCount")) is int and element["showCount"] == 2 and
                    element.get("showZero") is True, f"{label} must use two zero-padded digits")
            require(type(element.get("align")) is int and element["align"] == 1,
                    f"{label} requires native align=1 (left); align=0 is right")
            require(type(element.get("spacing", 0)) is int and element.get("spacing", 0) == 0,
                    f"{label} requires spacing=0")
            names = element.get("imageList")
            require(isinstance(names, list) and len(names) == 10, f"{label} needs ten ordered digit PNGs")
            sizes = [png_pixels(png_path(aod_folder, item))[0] for item in names]
            require(all(size == sizes[0] for size in sizes), f"{label} digit dimensions differ")
            rectangle = rect(element, sizes[0][0] * 2, sizes[0][1], label)
            clocks.append(source)
        else:
            raise ValidationError(f"{label}: unsupported AOD type {kind!r}; only static images and native digits allowed")
        rectangles.append(rectangle)
    require(aod[0].get("type") == "element" and rectangles[0] == [0, 0, WIDTH, HEIGHT],
            "First AOD element must be a complete 336x480 background at (0,0)")
    require(sorted(clocks) == ["0811", "1011"], "AOD needs exactly one hour widget and one minute widget")
    report = {"result": "PASS", "profile": profile, "canvas": [WIDTH, HEIGHT],
              "name": name, "id": ident, "header_flags": 4, "normal_resources": len(source_assets),
              "ordinary_geometry_entries_checked": geometry_count,
              "aod_elements": len(aod), "aod_rectangles": rectangles,
              "scope": "File references, PNG geometry and supported configuration; does not execute Lua or certify hardware"}
    return definition, source_assets, report


def u16(data, offset):
    require(offset >= 0 and offset + 2 <= len(data), "Truncated 16-bit field")
    return struct.unpack_from("<H", data, offset)[0]


def u32(data, offset):
    require(offset >= 0 and offset + 4 <= len(data), "Truncated 32-bit field")
    return struct.unpack_from("<I", data, offset)[0]


def u24(data, offset):
    require(offset >= 0 and offset + 3 <= len(data), "Truncated 24-bit field")
    return int.from_bytes(data[offset:offset + 3], "little")


def parse_face(data, header):
    require(header + 0x58 <= len(data), "Truncated face header")
    sections, ranges, tables = [], [], []
    for kind in range(10):
        count, offset = u32(data, header + 8 + kind * 8), u32(data, header + 12 + kind * 8)
        require(count <= 4096 and offset % 4 == 0 and offset + count * 16 <= len(data), "Invalid section table")
        require(not count or offset >= 0x158, "Section table overlaps headers")
        if count:
            tables.append((offset, offset + count * 16))
        records, indices = [], set()
        for i in range(count):
            pos = offset + i * 16
            idx, start, size = u16(data, pos), u32(data, pos + 8), u32(data, pos + 12)
            require(idx not in indices and data[pos + 3] == kind, "Duplicate index or incorrect definition kind")
            require(start % 4 == 0 and start >= 0x158 and size > 0 and start + size <= len(data),
                    "Resource payload outside package or not aligned")
            indices.add(idx)
            records.append((idx, start, size))
            ranges.append((start, start + size))
        sections.append(records)
    return sections, ranges, tables


def decode_rle(blob, sign, width, height):
    require(sign in (0, 16), f"Unsupported compressed AOD image sign: {sign}")
    bpp = 1 if sign == 16 else 4
    expected = width * height * bpp + (1024 if sign == 16 else 0)
    require(blob[:4] == bytes.fromhex("e021a55a"), "Incorrect native RLE signature")
    info = u32(blob, 4)
    require(info & 15 == bpp and info >> 4 == expected, "Incorrect RLE decoded size")
    output, pos = bytearray(), 8
    while pos < len(blob):
        control = blob[pos]
        pos += 1
        count = control & 127
        length = count * bpp if control & 128 else bpp
        require(count > 0 and pos + length <= len(blob), "Truncated or empty RLE command")
        chunk = blob[pos:pos + length]
        output.extend(chunk if control & 128 else chunk * count)
        pos += length
        require(len(output) <= expected, "RLE output overflow")
    require(len(output) == expected, "RLE output underflow")
    if sign == 16:
        return b"".join(output[index * 4:index * 4 + 4] for index in output[1024:])
    return bytes(output)


def decode_image(data, record, *, image_list=False):
    _, start, length = record
    blob = data[start:start + length]
    require(len(blob) >= 12, "Truncated native image")
    width, height = u16(blob, 4), u16(blob, 6)
    require(0 < width <= WIDTH and 0 < height <= HEIGHT, "Native image dimensions outside n67 canvas")
    require(u32(blob, 8) + 12 == len(blob), "Native image resource length mismatch")
    if image_list:
        require(blob[1] == 10 and blob[2] == 4 and len(blob) >= 52, "AOD font must contain ten BGRA glyphs")
        sizes, pos = [u32(blob, 12 + i * 4) for i in range(10)], 52
    else:
        require(blob[1] == 4, "Expected native BGRA image")
        sizes, pos = [len(blob) - 12], 12
    pixels = []
    for size in sizes:
        require(size > 8 and pos + size <= len(blob), "Truncated compressed image")
        pixels.append(decode_rle(blob[pos:pos + size], blob[0], width, height))
        pos += size
    require(pos == len(blob), "Trailing bytes in native image")
    return (width, height), pixels


def validate_package(package, project):
    """Validate independently of the external packer and compare all used assets."""
    definition, sources, _ = validate_project(project)
    package, project = Path(package), Path(project).resolve()
    require(0x158 <= package.stat().st_size <= MAX_PACKAGE_BYTES, "Package outside validator size limits")
    data = package.read_bytes()
    require(data[:4] == bytes.fromhex("5aa53412") and u32(data, 16) == 0x800, "Not a supported n67 raw package")
    require(data[28] == 2 and data[24] == data[29] == 0, "Expected two unshifted native face headers")
    require(u16(data, 30) == 4, "Packed AOD flag is wrong: header 0x1E must equal 4")
    require(data[40:58].split(b"\0")[0].decode("ascii") == str(definition["id"]), "Packed ID differs from project")
    require(data[104:164].split(b"\0")[0].decode("utf-8") == definition["name"], "Packed name differs from project")
    normal, normal_ranges, normal_tables = parse_face(data, 0xA8)
    aod, aod_ranges, aod_tables = parse_face(data, 0x100)
    require(len(normal[0]) == 1 and len(normal[5]) == len(sources) and
            sum(map(len, normal)) == len(sources) + 1, "Unsupported ordinary face structure")
    _, start, size = normal[0][0]
    entry = definition["elementsNormal"][0]
    require(size == 16 and data[start + 3] == 5 and
            [u16(data, start + 4), u16(data, start + 6)] == [entry.get("x", 0), entry.get("y", 0)],
            "Ordinary Lua entry differs from project")
    entry_index = u24(data, start)
    used, actual_entry = set(), None
    for index, start, size in normal[5]:
        blob = data[start:start + size]
        require(len(blob) >= 21, "Truncated Lua resource")
        rawlen, namelen = u24(blob, 0), blob[3]
        require(rawlen > 0 and rawlen + namelen + 20 == size and blob[4:20] == b"\0" * 16,
                "Invalid Lua resource lengths")
        name = blob[20:20 + namelen].decode("ascii")
        require(name in sources and name not in used, f"Unknown or duplicate packed resource: {name}")
        used.add(name)
        if index == entry_index:
            actual_entry = name
        payload, source = blob[20 + namelen:], sources[name]
        if source["kind"] in ("lua", "bin"):
            require(payload == source["path"].read_bytes(), f"Packed bytes differ from source: {name}")
        else:
            size, pixels = raw_lvgl(payload, name)
            expected_size, expected_pixels = png_pixels(source["path"])
            require(size == expected_size and pixels == expected_pixels, f"Packed pixels differ from source: {name}")
    require(used == set(sources) and actual_entry == entry["jsFileName"], "Lua entry/resource set mismatch")
    require(u32(data, 0x104) == 0, "Unexpected separate AOD selection preview")
    elements = definition["elementsAod"]
    require(len(aod[0]) == len(elements) and all(not aod[k] for k in (1, 4, 5, 6, 8, 9)),
            "AOD contains unsupported Lua, animation or other element types")
    by_kind = [{r[0]: r for r in records} for records in aod]
    used_aod = {2: set(), 3: set(), 7: set()}
    for order, (element, record) in enumerate(zip(elements, aod[0])):
        idx, start, length = record
        require(idx == order and length == 16, "AOD element ordering or size differs")
        require([u16(data, start + 4), u16(data, start + 6)] == [element.get("x", 0), element.get("y", 0)],
                f"AOD element {order} position differs")
        ref, kind = u24(data, start), data[start + 3]
        expected_kind = 2 if element["type"] == "element" else 7
        require(kind == expected_kind and ref in by_kind[kind], "AOD element reference is invalid")
        used_aod[kind].add(ref)
        if kind == 2:
            size, frames = decode_image(data, by_kind[2][ref])
            names = [element["image"]]
        else:
            _, prop, prop_length = by_kind[7][ref]
            require(prop_length == 20, "Unexpected native digit widget size")
            require(data[prop:prop + 2].hex().upper() == element["dataSrc"], "Packed time data source differs")
            require(data[prop + 2] == 2 and data[prop + 3] == 0x15,
                    "Packed clock must be two zero-padded digits with native left align=1 (byte 0x15)")
            require(data[prop + 13] == 0 and data[prop + 11] == 3 and data[prop + 19] == 0,
                    "Unsupported native clock spacing or font reference")
            font_index = u24(data, prop + 8)
            require(font_index in by_kind[3], "Missing native clock font")
            used_aod[3].add(font_index)
            size, frames = decode_image(data, by_kind[3][font_index], image_list=True)
            names = element["imageList"]
        require(len(frames) == len(names), "AOD image count differs")
        for name, pixels in zip(names, frames):
            source_size, source_pixels = png_pixels(png_path(project / "images_aod", name))
            require(size == source_size and pixels == source_pixels, f"AOD pixels differ from source: {name}")
    require(all(used_aod[k] == set(by_kind[k]) for k in used_aod), "Unreferenced AOD resource data")
    preview = u32(data, 32)
    require(preview % 4 == 0 and preview >= 0x158 and preview + 12 <= len(data), "Invalid preview offset")
    preview_length = 12 + u32(data, preview + 8)
    require(preview + preview_length <= len(data), "Truncated preview payload")
    preview_size, preview_frames = decode_image(data, (0, preview, preview_length))
    source_size, source_pixels = png_pixels(png_path(project / "images", definition["previewImg"]), preview=True)
    require(preview_size == source_size and preview_frames == [source_pixels], "Package preview pixels differ")
    # Exact shared resources within AOD are allowed; partial overlaps are not.
    require(not set(normal_ranges).intersection(aod_ranges), "Normal and AOD resources alias")
    tables = normal_tables + aod_tables
    payloads = normal_ranges + aod_ranges + [(preview, preview + preview_length)]
    require(len(set(tables)) == len(tables), "Definition tables alias each other")
    require(not set(tables).intersection(payloads), "Definition table aliases a resource")
    spans = sorted(set(payloads + tables))
    require(all(end <= start for (_, end), (start, _) in zip(spans, spans[1:])),
            "Package tables or resource payloads partially overlap")
    return {"result": "PASS", "profile": "n67", "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(), "header_flags": 4,
            "face_count": 2, "normal_resources": len(sources), "aod_elements": len(elements),
            "all_source_bytes_or_pixels_equal": True,
            "scope": "Independent package structure and asset equality; no firmware, Lua execution or installation claim"}
