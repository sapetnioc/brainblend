#!/usr/bin/env python3
"""Build an installable Blender extension zip in dist/.

Downloads the pure-Python wheels listed in tools/wheels.txt into
brainblend/wheels/ (if missing), checks that they match blender_manifest.toml,
then zips the package. Install the result in Blender with
Edit > Preferences > Get Extensions > Install from Disk.
"""

import pathlib
import re
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "brainblend"
WHEELS = PACKAGE / "wheels"


def main():
    WHEELS.mkdir(exist_ok=True)
    requirements = (ROOT / "tools" / "wheels.txt").read_text().split()
    manifest = (PACKAGE / "blender_manifest.toml").read_text()
    listed = re.findall(r'"\./wheels/([^"]+\.whl)"', manifest)
    if not all((WHEELS / name).exists() for name in listed):
        subprocess.check_call(
            [sys.executable, "-m", "pip", "download", "--no-deps", "--only-binary=:all:", "-d", str(WHEELS), *requirements]
        )
    present = sorted(p.name for p in WHEELS.glob("*.whl"))
    missing = [name for name in listed if name not in present]
    if missing:
        sys.exit(f"Wheels listed in blender_manifest.toml but not downloaded: {missing}")

    version = re.search(r'^version = "([^"]+)"', manifest, re.M).group(1)
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    out = dist / f"brainblend-{version}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(PACKAGE.rglob("*")):
            rel = path.relative_to(PACKAGE)
            if path.is_dir() or "__pycache__" in rel.parts or path.suffix == ".pyc":
                continue
            if rel.parts[0] == "wheels" and path.name not in listed:
                continue
            zf.write(path, rel.as_posix())
    print(out)


if __name__ == "__main__":
    main()
