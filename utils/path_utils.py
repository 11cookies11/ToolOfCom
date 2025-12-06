from __future__ import annotations

import sys
from pathlib import Path


def get_app_base_dir() -> Path:
    """
    Return the base directory for bundled/static resources.

    - In a PyInstaller onefile build, sys._MEIPASS points to the temp dir where
      bundled data files are unpacked.
    - In a frozen build without _MEIPASS, fall back to the executable's folder.
    - In normal source execution, use the project root (parent of utils/).
    """
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resolve_resource_path(path: str | Path) -> Path:
    """
    Resolve a resource path for both source and PyInstaller builds.

    Preference order:
    1) Absolute paths are returned unchanged.
    2) If the path exists relative to the current working directory, use it.
    3) Otherwise, resolve under the application base directory.
    """
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate

    cwd_candidate = Path.cwd() / candidate
    if cwd_candidate.exists():
        return cwd_candidate

    if getattr(sys, "frozen", False):
        exe_dir_candidate = Path(sys.executable).resolve().parent / candidate
        if exe_dir_candidate.exists():
            return exe_dir_candidate

    return get_app_base_dir() / candidate
