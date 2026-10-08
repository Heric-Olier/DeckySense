"""DeckySense self-updater.

Checks GitHub releases and installs the latest zip in place, then asks
Decky's plugin loader to restart so the new code takes effect.

Pattern ported from Panel de Control (proven across ~120 releases):

- Every public function NEVER raises — it returns a status dict so the
  UI renders a message instead of hanging on a spinner.
- ``_operation_lock`` serialises check/install (the panel, the modal and
  the tab badge can all fire calls at once).
- ``install()`` stages the download in a temp dir, restores the unix
  permission bits recorded in the zip (plain ``extractall()`` drops
  them), then copies item-by-item OVER the installed plugin dir — the
  directory is never replaced, so imports and ``sys.path`` stay intact.
  Settings live in ``DECKY_PLUGIN_SETTINGS_DIR`` and are untouched.
- ``restart_loader()`` sanitises ``LD_LIBRARY_PATH`` before calling
  systemctl (Decky's PyInstaller build points it at a bundled libcrypto
  and systemctl fails with "OPENSSL_x not found" otherwise).

Repo-specific values are read at runtime, so the module stays a single
source of truth:
  - GitHub repo slug = ``package.json`` "name"   (Heric-Olier/deckysense)
  - zip / dir name   = ``plugin.json`` "name"    ("DeckySense")
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import threading
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import decky

from deckysense.http_util import ssl_context
from deckysense.version import read_version

_GITHUB_OWNER = "Heric-Olier"
_UA = "decky-self-updater"

# Session cache: only hit GitHub once per plugin process (force=True bypasses it).
_cache: dict[str, Any] | None = None
_operation_lock = threading.RLock()


# ── Identity helpers ───────────────────────────────────────────────


def _plugin_dir() -> Path:
    # Layout: py_modules/deckysense/updater/self_updater.py -> plugin root.
    return Path(__file__).resolve().parent.parent.parent.parent


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _repo_slug() -> str:
    return str(_read_json(_plugin_dir() / "package.json").get("name", ""))


def _plugin_name() -> str:
    return str(_read_json(_plugin_dir() / "plugin.json").get("name", ""))


# ── Version helpers ────────────────────────────────────────────────

_SEMVER = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def _extract_semver(tag: str) -> str:
    """Pull the X.Y.Z out of a tag string (copes with release-please prefixes)."""
    m = _SEMVER.search(tag or "")
    return m.group(0) if m else ""


def _norm(v: str) -> tuple[int, int, int]:
    m = _SEMVER.search(v or "")
    if not m:
        return (0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _is_newer(latest: str, current: str) -> bool:
    return _norm(latest) > _norm(current)


# ── HTTP ───────────────────────────────────────────────────────────


def _http_get(url: str, accept: str) -> bytes:
    req = urllib.request.Request(
        url, headers={"User-Agent": _UA, "Accept": accept}
    )
    with urllib.request.urlopen(req, timeout=15, context=ssl_context()) as resp:  # noqa: S310
        return resp.read()


# ── Release shaping ────────────────────────────────────────────────


def _find_asset(data: dict[str, Any], latest: str) -> str:
    """Locate the release zip.

    The release workflow uploads ``deckysense-v<version>.zip`` (built by
    ``scripts/package.sh``). Prefer the asset whose name carries the
    latest version; fall back to any zip named after the plugin.
    """
    name = _plugin_name().lower()
    if not name:
        return ""
    fallback = ""
    for asset in data.get("assets") or []:
        aname = str(asset.get("name", "")).lower()
        if not aname.endswith(".zip") or name not in aname:
            continue
        url = str(asset.get("browser_download_url", ""))
        if latest and latest in aname:
            return url  # exact version match wins
        fallback = fallback or url
    return fallback


def _shape(data: dict[str, Any], current: str) -> dict[str, Any]:
    """Turn a GitHub 'releases/latest' payload into the UpdateInfo dict."""
    latest = _extract_semver(str(data.get("tag_name", "")))
    notes = str(data.get("body", "") or "")
    download_url = _find_asset(data, latest)
    return {
        "current": current,
        "latest": latest or current,
        "notes": notes,
        "download_url": download_url,
        "has_update": bool(latest) and bool(download_url) and _is_newer(latest, current),
        "error": "",
    }


def _release_notes(data: list[dict[str, Any]], current: str, latest: str) -> str:
    """Aggregate the notes of every release between current and latest.

    The update modal then shows everything the user missed, newest first.
    """
    releases: dict[str, dict[str, Any]] = {}
    for release in data:
        if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
            continue
        version = _extract_semver(str(release.get("tag_name", "")))
        if version and _is_newer(version, current) and not _is_newer(version, latest):
            releases.setdefault(version, release)

    notes: list[str] = []
    for version in sorted(releases, key=_norm, reverse=True):
        release = releases[version]
        body = str(release.get("body", "") or "").strip()
        notes.append(f"## v{version}" + (f"\n\n{body}" if body else ""))
    return "\n\n".join(notes)


def _fetch_releases(slug: str) -> list[dict[str, Any]]:
    releases: list[dict[str, Any]] = []
    page = 1
    while True:
        api = (
            f"https://api.github.com/repos/{_GITHUB_OWNER}/{slug}/releases"
            f"?per_page=100&page={page}"
        )
        batch = json.loads(_http_get(api, "application/vnd.github+json"))
        if not isinstance(batch, list):
            raise ValueError("unexpected releases response")
        releases.extend(batch)
        if len(batch) < 100:
            return releases
        page += 1


# ── Public API ─────────────────────────────────────────────────────


def check(force: bool = False) -> dict[str, Any]:
    """Query GitHub for the latest release. Cached per session.

    Never raises: returns the UpdateInfo dict with an ``error`` code on
    failure. Pass ``force=True`` to bypass the cache (manual button).
    """
    global _cache
    with _operation_lock:
        if _cache is not None and not force:
            return _cache

        current = read_version()
        empty: dict[str, Any] = {
            "current": current,
            "latest": current,
            "notes": "",
            "download_url": "",
            "has_update": False,
            "error": "",
        }
        result = empty
        latest_loaded = False
        try:
            slug = _repo_slug()
            latest_api = f"https://api.github.com/repos/{_GITHUB_OWNER}/{slug}/releases/latest"
            latest_data = json.loads(_http_get(latest_api, "application/vnd.github+json"))
            latest_loaded = True
            result = _shape(latest_data, current)
            if result["has_update"]:
                releases = [latest_data, *_fetch_releases(slug)]
                result["notes"] = _release_notes(releases, current, result["latest"])
        except urllib.error.HTTPError as e:
            if e.code == 404 and not latest_loaded:
                decky.logger.info("[updater] no published release yet")
            else:
                decky.logger.warning(f"[updater] check failed: {e}")
                result = {**empty, "error": "network"}
        except Exception as e:  # noqa: BLE001 — must never propagate to the UI
            decky.logger.warning(f"[updater] check failed: {e}")
            result = {**empty, "error": "network"}
        _cache = result
        return result


def _extract_zip(zf: zipfile.ZipFile, dest: Path) -> None:
    """Extract preserving the unix permission bits the archive records.

    Plain ``extractall()`` drops them, so a bundled executable would land
    non-executable and fail to run. A zip with no recorded mode
    (``external_attr`` high bits == 0) keeps the default extract.
    """
    for info in zf.infolist():
        out = zf.extract(info, dest)
        # Low 9 bits only (rwx for u/g/o); never carry setuid/setgid/sticky.
        mode = (info.external_attr >> 16) & 0o777
        if mode:
            os.chmod(out, mode)


def install() -> dict[str, Any]:
    """Download the latest release zip and overwrite the installed dir.

    Returns ``{ok, needs_restart, message}``. Never raises.
    """
    with _operation_lock:
        info = check()
        url = str(info.get("download_url") or "")
        if not info.get("has_update") or not url:
            return {"ok": False, "needs_restart": False, "message": "no_asset"}
        try:
            plugin_dir = _plugin_dir()
            name = _plugin_name()
            blob = _http_get(url, "application/octet-stream")
            with tempfile.TemporaryDirectory() as tmp:
                tmpd = Path(tmp)
                zpath = tmpd / "update.zip"
                zpath.write_bytes(blob)
                extract = tmpd / "x"
                with zipfile.ZipFile(zpath) as zf:
                    _extract_zip(zf, extract)
                src = extract / name  # top folder == plugin.json name
                if not src.is_dir():
                    subdirs = [p for p in extract.iterdir() if p.is_dir()]
                    if len(subdirs) == 1:
                        src = subdirs[0]
                if not src.is_dir():
                    return {"ok": False, "needs_restart": False, "message": "bad_zip"}
                # Copy over the installed plugin dir. User settings live in
                # DECKY_PLUGIN_SETTINGS_DIR (outside this dir) and are untouched.
                for item in src.iterdir():
                    dest = plugin_dir / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest)
            read_version.cache_clear()
            _mark_installed()
            return {"ok": True, "needs_restart": True, "message": "installed"}
        except Exception as e:  # noqa: BLE001
            decky.logger.error(f"[updater] install failed: {e}")
            return {"ok": False, "needs_restart": False, "message": "install_failed"}


def restart_loader() -> None:
    """Restart Decky to load the just-installed files.

    Fire-and-forget: this call kills the current process. The
    LD_LIBRARY_PATH sanitisation is what makes systemctl work at all
    from inside Decky's PyInstaller environment.
    """
    try:
        import subprocess

        env = dict(os.environ)
        orig = env.pop("LD_LIBRARY_PATH_ORIG", None)
        if orig is not None:
            env["LD_LIBRARY_PATH"] = orig
        else:
            env.pop("LD_LIBRARY_PATH", None)
        subprocess.Popen(  # noqa: S603
            ["/usr/bin/systemctl", "restart", "plugin_loader"],
            env=env,
            start_new_session=True,
        )
    except Exception as e:  # noqa: BLE001
        decky.logger.error(f"[updater] restart failed: {e}")


def _mark_installed() -> None:
    global _cache
    if _cache:
        _cache = {
            **_cache,
            "current": _cache.get("latest", _cache.get("current")),
            "has_update": False,
        }
