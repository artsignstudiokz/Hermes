"""Generate all icon sizes / formats from the source logo + favicon PNGs.

Run once after updating the source PNGs in `Downloads/`:

    python scripts/generate_icons.py

Outputs (all paths relative to repo root):
    frontend/public/icons/icon-192.png
    frontend/public/icons/icon-512.png
    frontend/public/icons/icon-maskable-512.png
    frontend/public/favicon.ico                — 16/32/48/256 multi-size
    packaging/windows/assets/app-icon.ico       — 16/32/48/256 multi-size
    packaging/windows/assets/installer-banner.bmp     — 164×314 wizard side image
    packaging/windows/assets/installer-header.bmp     — 150×57 wizard header
    packaging/windows/assets/splash.png         — desktop launcher splash
    landing/public/favicon.ico
    packaging/macos/app-icon.icns               — best-effort (Pillow >=10)
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent

LOGO = ROOT / "frontend" / "public" / "hermes-logo.png"
FAVICON = ROOT / "frontend" / "public" / "hermes-favicon.png"

GOLD = "#C9A96E"
NAVY = "#1B2940"
MARBLE = "#FBF7EC"


def fit_into(canvas_size: tuple[int, int], src: Image.Image, *, padding: float = 0.1) -> Image.Image:
    """Center `src` on a transparent canvas, scaling to fit with `padding` margin."""
    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    cw, ch = canvas_size
    pad_w, pad_h = int(cw * padding), int(ch * padding)
    target_w, target_h = cw - 2 * pad_w, ch - 2 * pad_h
    src_ratio = src.width / src.height
    target_ratio = target_w / target_h
    if src_ratio > target_ratio:
        new_w = target_w
        new_h = int(target_w / src_ratio)
    else:
        new_h = target_h
        new_w = int(target_h * src_ratio)
    resized = src.resize((new_w, new_h), Image.LANCZOS)
    canvas.paste(resized, ((cw - new_w) // 2, (ch - new_h) // 2), resized)
    return canvas


def with_background(img: Image.Image, color: str) -> Image.Image:
    bg = Image.new("RGBA", img.size, color)
    bg.alpha_composite(img)
    return bg


def make_app_icons() -> None:
    favicon = Image.open(FAVICON).convert("RGBA")

    icons_dir = ROOT / "frontend" / "public" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)

    # 192 / 512 — transparent edges (any-purpose).
    for size in (192, 512):
        out = fit_into((size, size), favicon, padding=0.08)
        out.save(icons_dir / f"icon-{size}.png", optimize=True)

    # Maskable: pad more so safe-area mask doesn't crop the wings.
    masked = fit_into((512, 512), favicon, padding=0.22)
    masked = with_background(masked, MARBLE)
    masked.save(icons_dir / "icon-maskable-512.png", optimize=True)

    print(f"  ->{icons_dir.relative_to(ROOT)}/icon-{{192,512,maskable-512}}.png")


def make_ico_files() -> None:
    favicon = Image.open(FAVICON).convert("RGBA")
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

    base = fit_into((256, 256), favicon, padding=0.10)
    base_bg = with_background(base, MARBLE)  # ICO benefits from a non-transparent base

    targets = [
        ROOT / "frontend" / "public" / "favicon.ico",
        ROOT / "landing" / "public" / "favicon.ico",
        ROOT / "packaging" / "windows" / "assets" / "app-icon.ico",
    ]
    for path in targets:
        path.parent.mkdir(parents=True, exist_ok=True)
        base_bg.save(path, sizes=sizes)
        print(f"  ->{path.relative_to(ROOT)}")


def make_installer_banner() -> None:
    """Inno Setup wizard side image: 164×314 BMP."""
    favicon = Image.open(FAVICON).convert("RGBA")
    banner = Image.new("RGB", (164, 314), MARBLE)

    # Vertical gold gradient along the left edge (3px) for a premium feel.
    draw = ImageDraw.Draw(banner)
    for y in range(314):
        # Marble → faint gold tint top-to-bottom.
        t = y / 314
        r = int(0xFB + (0xC9 - 0xFB) * 0.06 * t)
        g = int(0xF7 + (0xA9 - 0xF7) * 0.06 * t)
        b = int(0xEC + (0x6E - 0xEC) * 0.06 * t)
        draw.line([(0, y), (163, y)], fill=(r, g, b))

    # Logo centered-upper.
    logo_box = fit_into((140, 220), favicon, padding=0.10)
    banner.paste(logo_box, ((164 - 140) // 2, 30), logo_box)

    # Wordmark beneath.
    try:
        font = ImageFont.truetype("arialbd.ttf", 18)
        font_sub = ImageFont.truetype("arial.ttf", 11)
    except OSError:
        font = ImageFont.load_default()
        font_sub = ImageFont.load_default()
    draw.text((164 // 2, 260), "HERMES", fill=NAVY, font=font, anchor="mm")
    draw.text((164 // 2, 280), "TRADING BOT", fill="#5b6571", font=font_sub, anchor="mm")
    draw.text((164 // 2, 296), "by BAI Core", fill=GOLD, font=font_sub, anchor="mm")

    out = ROOT / "packaging" / "windows" / "assets" / "installer-banner.bmp"
    banner.save(out, format="BMP")
    print(f"  ->{out.relative_to(ROOT)}")


def make_installer_header() -> None:
    """Inno Setup wizard header strip: 150×57 BMP."""
    favicon = Image.open(FAVICON).convert("RGBA")
    header = Image.new("RGB", (150, 57), MARBLE)
    icon = fit_into((48, 48), favicon, padding=0.05)
    header.paste(icon, (4, 4), icon)
    draw = ImageDraw.Draw(header)
    try:
        font = ImageFont.truetype("arialbd.ttf", 13)
        font_sub = ImageFont.truetype("arial.ttf", 10)
    except OSError:
        font = ImageFont.load_default()
        font_sub = ImageFont.load_default()
    draw.text((58, 14), "Hermes", fill=NAVY, font=font)
    draw.text((58, 32), "by BAI Core", fill=GOLD, font=font_sub)
    out = ROOT / "packaging" / "windows" / "assets" / "installer-header.bmp"
    header.save(out, format="BMP")
    print(f"  ->{out.relative_to(ROOT)}")


def make_splash() -> None:
    """Native Tk splash image used by desktop/splash.py — 240×120 PNG on dark."""
    favicon = Image.open(FAVICON).convert("RGBA")
    splash = Image.new("RGBA", (240, 120), (251, 247, 236, 255))
    icon = fit_into((220, 100), favicon, padding=0.08)
    splash.paste(icon, ((240 - 220) // 2, 10), icon)
    out = ROOT / "packaging" / "windows" / "assets" / "splash.png"
    splash.save(out, optimize=True)
    print(f"  ->{out.relative_to(ROOT)}")


def make_icns() -> None:
    """macOS .icns — Pillow ≥10 supports writing .icns; otherwise warn."""
    favicon = Image.open(FAVICON).convert("RGBA")
    icon_512 = fit_into((1024, 1024), favicon, padding=0.10)
    out = ROOT / "packaging" / "macos" / "app-icon.icns"
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        icon_512.save(out)
        print(f"  ->{out.relative_to(ROOT)}")
    except (KeyError, ValueError) as e:
        # Older Pillow lacks .icns writer — fall back to PNG.
        png_path = out.with_suffix(".png")
        icon_512.save(png_path)
        print(f"  WARN: {out.name} not supported by this Pillow ({e}); wrote {png_path.name} instead")


def main() -> None:
    if not LOGO.exists() or not FAVICON.exists():
        raise SystemExit(
            f"Source images missing.\n"
            f"  Logo:     {LOGO}\n"
            f"  Favicon:  {FAVICON}\n"
            f"Place hermes-logo.png + hermes-favicon.png in frontend/public/ first.",
        )
    print("Generating Hermes icon assets…")
    make_app_icons()
    make_ico_files()
    make_installer_banner()
    make_installer_header()
    make_splash()
    make_icns()
    print("Done.")


if __name__ == "__main__":
    main()
