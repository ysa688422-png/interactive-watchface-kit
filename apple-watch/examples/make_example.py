#!/usr/bin/env python3
"""Generate original geometric example artwork. No external image assets."""
from pathlib import Path
import json
from PIL import Image, ImageDraw


def main():
    destination = Path(__file__).parent / "generated"
    destination.mkdir(exist_ok=True)
    image = Image.new("RGBA", (360, 440))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((75, 130, 285, 410), radius=60, fill="#81719F")
    draw.ellipse((80, 25, 280, 225), fill="#F3D3B6")
    draw.arc((135, 130, 225, 175), 0, 180, fill="#665272", width=6)
    draw.ellipse((125, 110, 137, 122), fill="#665272")
    draw.ellipse((223, 110, 235, 122), fill="#665272")
    image.save(destination / "geometric-friend.png")
    manifest = {"photos": [{"name": "geometric-friend", "source": "geometric-friend.png"}]}
    (destination / "photos.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(destination / "photos.json")


if __name__ == "__main__":
    main()
