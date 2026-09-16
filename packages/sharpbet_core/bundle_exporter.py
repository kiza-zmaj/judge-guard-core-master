#!/usr/bin/env python3
"""
SharpBet Core - Standalone Bundle Exporter
Packages the complete, isolated SharpBet Core quantitative engine into a
clean ZIP distribution archive ready for sale on Acquire.com, Flippa, or client delivery.
"""

import os
from pathlib import Path
import zipfile


def create_bundle():
    root_dir = Path(__file__).resolve().parent.parent.parent
    pkg_dir = root_dir / "packages" / "sharpbet_core"
    export_dir = root_dir / "exports" / "dist"
    export_dir.mkdir(parents=True, exist_ok=True)

    zip_path = export_dir / "sharpbet_core_v3.0.0.zip"

    print("📦 Packaging SharpBet Core standalone distribution...")
    print(f"   Root source: {root_dir}")
    print(f"   Target archive: {zip_path}")

    files_to_include = [
        (pkg_dir / "README.md", "README.md"),
        (pkg_dir / "requirements.txt", "requirements.txt"),
        (pkg_dir / "pyproject.toml", "pyproject.toml"),
        (pkg_dir / "Dockerfile", "Dockerfile"),
        (pkg_dir / "docker-compose.yml", "docker-compose.yml"),
        (pkg_dir / "ACQUIRE_LISTING_PITCH.md", "ACQUIRE_LISTING_PITCH.md"),
        (root_dir / "tests" / "test_sharpbet_core.py", "tests/test_sharpbet_core.py"),
    ]

    # Directories to recursively include
    dirs_to_include = [
        (root_dir / "unified_betting_core", "unified_betting_core"),
    ]

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add single files
        for src_path, arc_name in files_to_include:
            if src_path.exists():
                zf.write(src_path, arc_name)
                print(f"   + [FILE] {arc_name}")
            else:
                print(f"   ⚠️ Warning: Missing {src_path}")

        # Add directories
        for src_dir, arc_prefix in dirs_to_include:
            if not src_dir.exists():
                print(f"   ⚠️ Warning: Directory missing {src_dir}")
                continue
            for root, dirs, files in os.walk(src_dir):
                # Prune cache directories
                dirs[:] = [d for d in dirs if d not in ("__pycache__", ".pytest_cache")]
                for f in files:
                    if f.endswith((".pyc", ".pyo")):
                        continue
                    full_path = Path(root) / f
                    rel_path = full_path.relative_to(src_dir)
                    arc_name = f"{arc_prefix}/{rel_path}"
                    zf.write(full_path, arc_name)

        print(f"   + [DIR]  {arc_prefix} (recursive)")

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print("\n✅ Successfully generated standalone bundle:")
    print(f"   Path: {zip_path}")
    print(f"   Size: {size_mb:.2f} MB")
    print("   Ready for Acquire.com / Flippa / Client delivery!\n")
    return str(zip_path)


if __name__ == "__main__":
    create_bundle()
