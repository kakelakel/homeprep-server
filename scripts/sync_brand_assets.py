"""Fetch the canonical HomePrep brand assets from the HA integration repository.

The Home Assistant integration owns the canonical icon/logo files. Server/Web builds
pin to a known HomePrep commit so all distributions use the same branding without
copying divergent binary assets into multiple repositories.
"""

from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

BRAND_REF = "9e4254e59382ffb9c665960110d4bcc1b113b87f"
BRAND_BASE = f"https://raw.githubusercontent.com/kakelakel/homeprep/{BRAND_REF}/custom_components/homeprep/brand"


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 - pinned GitHub source
        destination.write_bytes(response.read())


def sync_web(root: Path) -> None:
    public = root / "web" / "public"
    download(f"{BRAND_BASE}/icon.png", public / "homeprep-icon.png")
    download(f"{BRAND_BASE}/logo.png", public / "homeprep-logo.png")


def sync_windows(root: Path) -> None:
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - build-time dependency only
        raise SystemExit("Pillow is required for --windows brand asset generation") from exc

    assets = root / "packaging" / "windows" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    icon_png = assets / "homeprep-icon.png"
    logo_png = assets / "homeprep-logo.png"
    download(f"{BRAND_BASE}/icon.png", icon_png)
    download(f"{BRAND_BASE}/logo.png", logo_png)

    with Image.open(icon_png) as icon:
        icon = icon.convert("RGBA")
        icon.save(
            assets / "homeprep.ico",
            format="ICO",
            sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        )
        icon.resize((55, 55), Image.Resampling.LANCZOS).convert("RGB").save(
            assets / "wizard-small.bmp",
            format="BMP",
        )

    with Image.open(logo_png) as logo:
        logo = logo.convert("RGB")
        target_width, target_height = 164, 314
        logo.thumbnail((target_width - 14, target_height - 18), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (target_width, target_height), "white")
        left = (target_width - logo.width) // 2
        top = (target_height - logo.height) // 2
        canvas.paste(logo, (left, top))
        canvas.save(assets / "wizard-large.bmp", format="BMP")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--windows", action="store_true", help="Also generate Windows installer assets")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sync_web(root)
    if args.windows:
        sync_windows(root)


if __name__ == "__main__":
    main()
