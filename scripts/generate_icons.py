#!/usr/bin/env python3
"""Generate FinanceApp icons from a single vector-like Pillow drawing.

Run from the repository root:

    python3 scripts/generate_icons.py

The script only needs Pillow. It writes Tauri icons, the browser favicon and
the Apple touch icon. Keeping the artwork in code makes icon updates
reproducible and avoids checking binary source files into git.
"""

from __future__ import annotations

import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
TAURI_ICONS = ROOT / "src-tauri" / "icons"
STATIC = ROOT / "src-frontend" / "static"
SIZE = 1024


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def gradient(size: int, start: tuple[int, int, int], end: tuple[int, int, int]) -> Image.Image:
    """Diagonal gradient from top-left to bottom-right."""
    image = Image.new("RGBA", (size, size))
    pixels = image.load()
    assert pixels is not None
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            pixels[x, y] = (
                round(lerp(start[0], end[0], t)),
                round(lerp(start[1], end[1], t)),
                round(lerp(start[2], end[2], t)),
                255,
            )
    return image


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((40, 40, size - 40, size - 40), radius=radius, fill=255)
    return mask


def draw_icon() -> Image.Image:
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    # Drop shadow behind the rounded tile.
    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (62, 82, SIZE - 62, SIZE - 42), radius=220, fill=(15, 23, 42, 90)
    )
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(28)))

    tile = gradient(SIZE, (13, 148, 136), (67, 56, 202))
    tile.putalpha(rounded_mask(SIZE, 224))
    canvas.alpha_composite(tile)

    # Top-left sheen.
    sheen = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(sheen).ellipse((80, 10, 860, 620), fill=(255, 255, 255, 34))
    sheen.putalpha(Image.composite(sheen.getchannel("A"), Image.new("L", (SIZE, SIZE), 0), rounded_mask(SIZE, 224)))
    canvas.alpha_composite(sheen.filter(ImageFilter.GaussianBlur(42)))

    draw = ImageDraw.Draw(canvas)

    # Wallet body.
    draw.rounded_rectangle((214, 338, 810, 728), radius=78, fill=(255, 255, 255, 246))
    draw.rounded_rectangle((214, 338, 810, 500), radius=78, fill=(241, 245, 249, 255))
    draw.rectangle((214, 452, 810, 500), fill=(241, 245, 249, 255))
    draw.line((238, 500, 786, 500), fill=(203, 213, 225, 255), width=6)

    # Card / clasp on the right.
    clasp = gradient(320, (15, 118, 110), (79, 70, 229)).resize((142, 96))
    clasp_mask = Image.new("L", clasp.size, 0)
    ImageDraw.Draw(clasp_mask).rounded_rectangle((0, 0, 141, 95), radius=30, fill=255)
    clasp.putalpha(clasp_mask)
    canvas.alpha_composite(clasp, (716, 498))
    draw.ellipse((762, 526, 802, 566), fill=(255, 255, 255, 235))

    # Rising bars: the core "finance" motif.
    bars = (
        ((330, 548, 392, 662), (13, 148, 136)),
        ((430, 496, 492, 662), (20, 184, 166)),
        ((530, 444, 592, 662), (79, 70, 229)),
    )
    for (x0, y0, x1, y1), color in bars:
        draw.rounded_rectangle((x0, y0, x1, y1), radius=20, fill=(*color, 255))

    # Small trend line above the bars.
    points = [(352, 512), (458, 468), (560, 418), (666, 370)]
    draw.line(points, fill=(15, 118, 110, 170), width=16, joint="curve")
    for x, y in points:
        draw.ellipse((x - 13, y - 13, x + 13, y + 13), fill=(255, 255, 255, 255), outline=(15, 118, 110, 255), width=7)

    # Gold coin.
    draw.ellipse((700, 238, 884, 422), fill=(251, 191, 36, 255), outline=(217, 119, 6, 255), width=10)
    draw.ellipse((724, 262, 860, 398), outline=(255, 255, 255, 110), width=7)
    coin_font = font(112)
    label = "Rp"
    box = draw.textbbox((0, 0), label, font=coin_font)
    text_w = box[2] - box[0]
    text_h = box[3] - box[1]
    draw.text(
        (792 - text_w / 2, 330 - text_h / 2 - box[1]),
        label,
        font=coin_font,
        fill=(120, 53, 15, 255),
    )

    # Sparkles.
    for x, y, r in ((884, 150, 12), (154, 252, 9), (918, 650, 8), (152, 704, 7)):
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 150))

    return canvas


def save_icns(source: Image.Image, destination: Path) -> None:
    """Write a modern PNG-based ICNS container."""
    variants = {
        b"icp4": 16,
        b"icp5": 32,
        b"icp6": 64,
        b"ic07": 128,
        b"ic08": 256,
        b"ic09": 512,
        b"ic10": 1024,
        b"ic11": 32,
        b"ic12": 64,
        b"ic13": 256,
        b"ic14": 512,
    }
    chunks = bytearray()
    for kind, size in variants.items():
        from io import BytesIO

        buffer = BytesIO()
        source.resize((size, size), Image.Resampling.LANCZOS).save(buffer, format="PNG")
        payload = buffer.getvalue()
        chunks += struct.pack(">4sI", kind, len(payload) + 8) + payload
    destination.write_bytes(b"icns" + struct.pack(">I", len(chunks) + 8) + bytes(chunks))


def main() -> None:
    icon = draw_icon()
    TAURI_ICONS.mkdir(parents=True, exist_ok=True)
    STATIC.mkdir(parents=True, exist_ok=True)

    icon.save(TAURI_ICONS / "icon.png", format="PNG")
    for size, name in (
        (32, "32x32.png"),
        (128, "128x128.png"),
        (256, "128x128@2x.png"),
        (512, "512x512.png"),
    ):
        icon.resize((size, size), Image.Resampling.LANCZOS).save(TAURI_ICONS / name, format="PNG")

    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon.save(TAURI_ICONS / "icon.ico", format="ICO", sizes=ico_sizes)
    save_icns(icon, TAURI_ICONS / "icon.icns")

    icon.resize((64, 64), Image.Resampling.LANCZOS).save(STATIC / "favicon.png", format="PNG")
    icon.resize((180, 180), Image.Resampling.LANCZOS).save(STATIC / "apple-touch-icon.png", format="PNG")

    print(f"Wrote icons to {TAURI_ICONS} and {STATIC}")


if __name__ == "__main__":
    main()
