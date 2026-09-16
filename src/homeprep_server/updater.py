from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox
from typing import Any


@dataclass(frozen=True)
class ReleaseInfo:
    tag_name: str
    html_url: str
    installer_url: str | None
    digest: str | None


def version_key(version: str) -> tuple[int, int, int, int]:
    clean = version.casefold().lstrip("v")
    numbers = [int(part) for part in re.findall(r"\d+", clean)[:3]]
    numbers.extend([0] * (3 - len(numbers)))
    stable = 0 if any(marker in clean for marker in ("dev", "alpha", "beta", "rc")) else 1
    return numbers[0], numbers[1], numbers[2], stable


def parse_release(payload: dict[str, Any]) -> ReleaseInfo:
    installer_url: str | None = None
    digest: str | None = None
    for asset in payload.get("assets", []):
        if asset.get("name") != "HomePrep-Setup.exe":
            continue
        installer_url = str(asset.get("browser_download_url") or "") or None
        raw_digest = asset.get("digest")
        digest = str(raw_digest) if raw_digest else None
        break
    return ReleaseInfo(
        tag_name=str(payload["tag_name"]),
        html_url=str(payload["html_url"]),
        installer_url=installer_url,
        digest=digest,
    )


def latest_release(release_api: str, installed_version: str) -> ReleaseInfo | None:
    request = urllib.request.Request(
        release_api,
        headers={"User-Agent": f"HomePrepServerManager/{installed_version}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    return parse_release(payload)


def _safe_version_name(version: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", version).strip("-") or "latest"


def download_installer(release: ReleaseInfo, installed_version: str) -> Path:
    if not release.installer_url:
        raise ValueError("The release does not contain HomePrep-Setup.exe")
    update_dir = Path(tempfile.gettempdir()) / "HomePrep" / "updates"
    update_dir.mkdir(parents=True, exist_ok=True)
    destination = update_dir / f"HomePrep-Setup-{_safe_version_name(release.tag_name)}.exe"
    request = urllib.request.Request(
        release.installer_url,
        headers={"User-Agent": f"HomePrepServerManager/{installed_version}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response, destination.open("wb") as target:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            target.write(chunk)

    if release.digest and release.digest.casefold().startswith("sha256:"):
        expected = release.digest.split(":", 1)[1].casefold()
        actual = hashlib.sha256(destination.read_bytes()).hexdigest().casefold()
        if actual != expected:
            destination.unlink(missing_ok=True)
            raise ValueError("Downloaded installer failed SHA-256 verification")
    return destination


def launch_installer(path: Path) -> None:
    if os.name != "nt":
        raise OSError("HomePrep automatic updates currently require Windows")
    os.startfile(str(path), "runas")  # type: ignore[attr-defined]


def check_for_updates(app, *, release_api: str, installed_version: str) -> None:
    try:
        release = latest_release(release_api, installed_version)
    except (OSError, urllib.error.URLError, KeyError, ValueError, json.JSONDecodeError) as exc:
        messagebox.showerror(
            "Update check failed",
            f"HomePrep could not check for updates.\n\n{exc}",
        )
        return

    if release is None:
        messagebox.showinfo(
            "HomePrep updates",
            "No published HomePrep Server release is available yet.",
        )
        return

    if version_key(release.tag_name) <= version_key(installed_version):
        messagebox.showinfo(
            "HomePrep updates",
            f"HomePrep Server {installed_version} is up to date.",
        )
        return

    if not release.installer_url:
        if messagebox.askyesno(
            "Update available",
            (
                f"Installed: {installed_version}\n"
                f"Latest: {release.tag_name}\n\n"
                "The release is available, but no Windows installer was attached. "
                "Open the release page?"
            ),
        ):
            webbrowser.open(release.html_url)
        return

    if not messagebox.askyesno(
        "Update available",
        (
            f"Installed: {installed_version}\n"
            f"Latest: {release.tag_name}\n\n"
            "Download and install the update now?\n\n"
            "HomePrep household data and backups are stored separately and are "
            "preserved during upgrades. Windows may ask for administrator permission."
        ),
    ):
        return

    try:
        app.configure(cursor="watch")
        app.update_idletasks()
        installer = download_installer(release, installed_version)
    except (OSError, urllib.error.URLError, ValueError) as exc:
        messagebox.showerror(
            "Update download failed",
            f"HomePrep could not download a verified installer.\n\n{exc}",
        )
        return
    finally:
        try:
            app.configure(cursor="")
        except Exception:
            pass

    if not messagebox.askyesno(
        "Install HomePrep update",
        (
            f"HomePrep Server {release.tag_name} is downloaded and verified.\n\n"
            "Start the installer now? The Server Manager will close while the "
            "upgrade is applied."
        ),
    ):
        return

    try:
        launch_installer(installer)
    except OSError as exc:
        messagebox.showerror(
            "Unable to start update",
            f"HomePrep could not start the installer.\n\n{exc}",
        )
        return

    app.after(250, app.destroy)
