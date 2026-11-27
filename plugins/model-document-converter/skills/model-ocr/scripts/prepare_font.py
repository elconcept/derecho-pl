#!/usr/bin/env python3
"""Locate the exact system font used by the 0.2.0 tests; never download it."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import sys

EXPECTED_SHA256 = "57f73e11f51999432bf7ab22ce55b6f945d5eca1bf824404cfa9ec2e3718c84e"
ASSET = Path(__file__).resolve().parents[1] / "assets" / "DejaVuSans.ttf"
SYSTEM_PATHS = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf"),
    Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
    Path("/usr/local/share/fonts/DejaVuSans.ttf"),
)


def verified(path: Path) -> bool:
    try:
        return (path.is_file() and path.stat().st_size == 759720
                and hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED_SHA256)
    except OSError:
        return False


def locate(source: Path | None = None) -> Path:
    if source is not None:
        if not verified(source):
            raise ValueError("Explicit font does not match the pinned SHA-256")
        return source.resolve()
    choices = [ASSET]
    if os.environ.get("MODEL_OCR_FONT"):
        choices.append(Path(os.environ["MODEL_OCR_FONT"]).expanduser())
    choices.extend(SYSTEM_PATHS)
    for path in choices:
        if verified(path):
            return path.resolve()
    raise ValueError("Exact DejaVuSans.ttf unavailable; install fonts-dejavu-core "
                     "from a trusted OS package repository or provide --source with the pinned SHA-256")


def install(source: Path) -> Path:
    if ASSET.exists():
        if not verified(ASSET):
            raise ValueError("Refusing to overwrite a different font in assets")
        return ASSET.resolve()
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Font changed after verification")
    ASSET.parent.mkdir(parents=True, exist_ok=True)
    with ASSET.open("xb") as output:
        output.write(data)
    if not verified(ASSET):
        raise ValueError("Installed font failed SHA-256 verification")
    return ASSET.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--install", action="store_true", help="Provision the writable local release/test directory")
    args = parser.parse_args()
    try:
        path = locate(args.source)
        print(install(path) if args.install else path)
        return 0
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
