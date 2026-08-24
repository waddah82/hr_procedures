"""Minimal zero-dependency PEP 517/660 backend for offline editable installs.

This backend exists so `pip install -e` can install this Frappe app without
trying to download a build backend from PyPI on isolated/offline servers.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import os
from pathlib import Path
import zipfile

NAME = "hr_procedures"
VERSION = "0.1.2"
DIST_INFO = f"{NAME}-{VERSION}.dist-info"


def _metadata_text() -> str:
    return (
        "Metadata-Version: 2.1\n"
        f"Name: {NAME}\n"
        f"Version: {VERSION}\n"
        "Summary: Employee violations and disciplinary procedures for Frappe HRMS\n"
        "Author: Shams Solutions\n"
        "License: MIT\n"
        "Requires-Python: >=3.10\n"
        "\n"
    )


def _wheel_text() -> str:
    return (
        "Wheel-Version: 1.0\n"
        "Generator: hr_procedures-offline-backend\n"
        "Root-Is-Purelib: true\n"
        "Tag: py3-none-any\n"
        "\n"
    )


def get_requires_for_build_wheel(config_settings=None):
    return []


def get_requires_for_build_editable(config_settings=None):
    return []


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    return _prepare_metadata(metadata_directory)


def prepare_metadata_for_build_editable(metadata_directory, config_settings=None):
    return _prepare_metadata(metadata_directory)


def _prepare_metadata(metadata_directory):
    target = Path(metadata_directory) / DIST_INFO
    target.mkdir(parents=True, exist_ok=True)
    (target / "METADATA").write_text(_metadata_text(), encoding="utf-8")
    (target / "WHEEL").write_text(_wheel_text(), encoding="utf-8")
    (target / "top_level.txt").write_text(f"{NAME}\n", encoding="utf-8")
    return DIST_INFO


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    # The .pth file keeps the Frappe app editable from apps/hr_procedures.
    project_root = str(Path(__file__).resolve().parent)
    files = {
        f"{NAME}.pth": project_root + "\n",
        f"{DIST_INFO}/METADATA": _metadata_text(),
        f"{DIST_INFO}/WHEEL": _wheel_text(),
        f"{DIST_INFO}/top_level.txt": f"{NAME}\n",
    }
    return _write_wheel(wheel_directory, files)


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    # Bench installs Frappe apps editable. Keep non-editable behavior usable by
    # packaging the Python package files directly when requested.
    root = Path(__file__).resolve().parent
    files = {
        f"{DIST_INFO}/METADATA": _metadata_text(),
        f"{DIST_INFO}/WHEEL": _wheel_text(),
        f"{DIST_INFO}/top_level.txt": f"{NAME}\n",
    }
    package_root = root / NAME
    for path in package_root.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            files[str(path.relative_to(root)).replace(os.sep, "/")] = path.read_bytes()
    return _write_wheel(wheel_directory, files)


def _write_wheel(wheel_directory, files):
    wheel_name = f"{NAME}-{VERSION}-py3-none-any.whl"
    wheel_path = Path(wheel_directory) / wheel_name
    wheel_path.parent.mkdir(parents=True, exist_ok=True)

    normalized = {}
    for name, content in files.items():
        if isinstance(content, str):
            content = content.encode("utf-8")
        normalized[name] = content

    record_rows = []
    for name, content in normalized.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode("ascii")
        record_rows.append((name, f"sha256={digest}", str(len(content))))

    record_name = f"{DIST_INFO}/RECORD"
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    for row in record_rows:
        writer.writerow(row)
    writer.writerow((record_name, "", ""))
    normalized[record_name] = output.getvalue().encode("utf-8")

    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in normalized.items():
            zf.writestr(name, content)
    return wheel_name
