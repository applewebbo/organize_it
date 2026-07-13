"""Generate PWA app icons from the source logo.

Run with: uv run python scripts/generate_pwa_icons.py

Produces, in static/img/:
- android-chrome-192x192.png / android-chrome-512x512.png (standard, transparent)
- apple-touch-icon.png (180x180, white background, no transparency)
- maskable-icon-512x512.png (logo scaled to the maskable safe zone on white)
"""

from pathlib import Path

from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
IMG_DIR = BASE_DIR / "static" / "img"
SOURCE = IMG_DIR / "logo.png"
BACKGROUND = (255, 255, 255, 255)
# Maskable icons must keep content inside a centred safe zone (~80% of canvas).
MASKABLE_SAFE_RATIO = 0.8


def _resized(source: Image.Image, size: int) -> Image.Image:
    return source.resize((size, size), Image.Resampling.LANCZOS)


def _on_background(icon: Image.Image, size: int) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), BACKGROUND)
    canvas.alpha_composite(icon)
    return canvas


def main() -> None:
    logo = Image.open(SOURCE).convert("RGBA")

    for size in (192, 512):
        _resized(logo, size).save(IMG_DIR / f"android-chrome-{size}x{size}.png")

    apple = _on_background(_resized(logo, 180), 180).convert("RGB")
    apple.save(IMG_DIR / "apple-touch-icon.png")

    maskable_size = 512
    inner = int(maskable_size * MASKABLE_SAFE_RATIO)
    offset = (maskable_size - inner) // 2
    canvas = Image.new("RGBA", (maskable_size, maskable_size), BACKGROUND)
    canvas.alpha_composite(_resized(logo, inner), (offset, offset))
    canvas.save(IMG_DIR / "maskable-icon-512x512.png")

    print("PWA icons generated in", IMG_DIR)


if __name__ == "__main__":
    main()
