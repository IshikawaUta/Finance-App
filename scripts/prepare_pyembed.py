#!/usr/bin/env python3
"""Prepare a portable Python runtime for standalone PyTauri bundles.

This script downloads a python-build-standalone distribution, extracts it to
``src-tauri/pyembed/python`` and installs the FinanceApp Python package into
it. It is used by GitHub Actions and can also be run locally when testing a
release build.

Examples
--------
    python3 scripts/prepare_pyembed.py
    python3 scripts/prepare_pyembed.py --target aarch64-apple-darwin
    python3 scripts/prepare_pyembed.py --release 20261021 --python-version 3.12.15

Only the Python standard library is required.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYEMBED = ROOT / "src-tauri" / "pyembed"
PYTHON_DIR = PYEMBED / "python"
CACHE = PYEMBED / ".cache"

DEFAULT_RELEASE = "20261021"
DEFAULT_PYTHON = "3.12.15"
RELEASE_URL = "https://github.com/astral-sh/python-build-standalone/releases/download"


def detect_target() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "linux":
        arch = {"x86_64": "x86_64", "amd64": "x86_64", "aarch64": "aarch64", "arm64": "aarch64"}.get(
            machine
        )
        if not arch:
            raise SystemExit(f"Unsupported Linux architecture: {machine}")
        return f"{arch}-unknown-linux-gnu"

    if system == "darwin":
        arch = {"x86_64": "x86_64", "amd64": "x86_64", "arm64": "aarch64", "aarch64": "aarch64"}.get(
            machine
        )
        if not arch:
            raise SystemExit(f"Unsupported macOS architecture: {machine}")
        return f"{arch}-apple-darwin"

    if system == "windows":
        arch = {"amd64": "x86_64", "x86_64": "x86_64", "arm64": "aarch64"}.get(machine)
        if not arch:
            raise SystemExit(f"Unsupported Windows architecture: {machine}")
        return f"{arch}-pc-windows-msvc"

    raise SystemExit(f"Unsupported operating system: {system}")


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and destination.stat().st_size > 0:
        print(f"Using cached archive: {destination}")
        return

    print(f"Downloading {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "FinanceApp-build/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, tempfile.NamedTemporaryFile(
        dir=destination.parent, delete=False
    ) as temporary:
        shutil.copyfileobj(response, temporary)
        temporary_path = Path(temporary.name)
    temporary_path.replace(destination)
    print(f"Saved {destination.stat().st_size / (1024 * 1024):.1f} MiB")


def fetch_checksums(release: str) -> dict[str, str]:
    url = f"{RELEASE_URL}/{release}/SHA256SUMS"
    request = urllib.request.Request(url, headers={"User-Agent": "FinanceApp-build/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        text = response.read().decode("utf-8")
    checksums: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2:
            checksums[parts[1].lstrip("*")] = parts[0].lower()
    return checksums


def verify_sha256(path: Path, expected: str) -> None:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != expected:
        raise SystemExit(f"Checksum mismatch for {path.name}: expected {expected}, got {actual}")
    print("Checksum verified")


def extract(archive: Path) -> None:
    if PYTHON_DIR.exists():
        print(f"Removing existing runtime: {PYTHON_DIR}")
        shutil.rmtree(PYTHON_DIR)
    PYEMBED.mkdir(parents=True, exist_ok=True)
    print(f"Extracting {archive.name}")
    with tarfile.open(archive, "r:gz") as tar:
        if hasattr(tarfile, "data_filter"):
            # The archive is downloaded from the pinned upstream release and
            # its SHA256 is verified above; the data filter additionally blocks
            # absolute paths and links escaping the destination.
            tar.extractall(PYEMBED, filter="data")
        else:  # pragma: no cover - Python < 3.12
            tar.extractall(PYEMBED)

    if not PYTHON_DIR.is_dir():
        # The archive normally contains a single top-level `python/` directory.
        candidates = [path for path in PYEMBED.iterdir() if path.is_dir() and path.name != ".cache"]
        if len(candidates) == 1:
            candidates[0].rename(PYTHON_DIR)
        else:
            raise SystemExit(f"Unexpected archive layout in {PYEMBED}")

    executable = python_executable()
    if not executable.is_file():
        raise SystemExit(f"Python executable not found at {executable}")
    print(f"Portable Python ready: {executable}")


def python_executable() -> Path:
    if os.name == "nt":
        return PYTHON_DIR / "python.exe"
    return PYTHON_DIR / "bin" / "python3"


def install_project() -> None:
    executable = python_executable()
    env = os.environ.copy()
    env["PYTAURI_STANDALONE"] = "1"
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env.setdefault("PYTHONUTF8", "1")

    pip_check = subprocess.run(
        [str(executable), "-m", "pip", "--version"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if pip_check.returncode != 0:
        print("pip is missing from the portable runtime; bootstrapping it")
        subprocess.run(
            [str(executable), "-m", "ensurepip", "--upgrade"],
            check=True,
            env=env,
        )

    command = [
        str(executable),
        "-m",
        "pip",
        "install",
        "--no-warn-script-location",
        "--force-reinstall",
        str(ROOT),
    ]
    print("Installing FinanceApp into the portable runtime")
    subprocess.run(command, check=True, env=env)


def prune() -> None:
    """Drop modules that a desktop finance app never uses."""
    candidates = [
        PYTHON_DIR / "lib" / "python3.12" / "test",
        PYTHON_DIR / "lib" / "python3.12" / "idlelib",
        PYTHON_DIR / "lib" / "python3.12" / "tkinter",
        PYTHON_DIR / "lib" / "python3.12" / "turtledemo",
        PYTHON_DIR / "lib" / "python3.12" / "ensurepip",
        PYTHON_DIR / "lib" / "python3.12" / "lib2to3",
        PYTHON_DIR / "Lib" / "test",
        PYTHON_DIR / "Lib" / "idlelib",
        PYTHON_DIR / "Lib" / "tkinter",
        PYTHON_DIR / "Lib" / "turtledemo",
        PYTHON_DIR / "Lib" / "ensurepip",
        PYTHON_DIR / "Lib" / "lib2to3",
        PYTHON_DIR / "share" / "man",
    ]
    for path in candidates:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)


def directory_size(path: Path) -> int:
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default=None, help="Rust/PBS target triple (auto-detected by default)")
    parser.add_argument("--release", default=os.getenv("PBS_RELEASE", DEFAULT_RELEASE))
    parser.add_argument("--python-version", default=os.getenv("PBS_PYTHON", DEFAULT_PYTHON))
    parser.add_argument("--skip-install", action="store_true", help="Only extract the runtime")
    parser.add_argument("--no-prune", action="store_true", help="Keep optional stdlib modules")
    parser.add_argument("--no-verify", action="store_true", help="Skip SHA256 verification")
    args = parser.parse_args()

    target = args.target or detect_target()
    filename = f"cpython-{args.python_version}+{args.release}-{target}-install_only_stripped.tar.gz"
    url = f"{RELEASE_URL}/{args.release}/{filename}"
    archive = CACHE / filename

    download(url, archive)

    if not args.no_verify:
        checksums = fetch_checksums(args.release)
        expected = checksums.get(filename)
        if not expected:
            raise SystemExit(f"No checksum published for {filename}")
        verify_sha256(archive, expected)

    extract(archive)
    if not args.skip_install:
        install_project()
        if not args.no_prune:
            prune()

    size = directory_size(PYTHON_DIR)
    print(f"Portable runtime size: {size / (1024 * 1024):.1f} MiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
