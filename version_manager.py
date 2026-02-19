#!/usr/bin/env python3
"""
version_manager.py — Lightweight file versioning for the LongevityPath project.

Usage as module:
    from version_manager import version_file, rollback, list_versions

Usage as CLI:
    python3 version_manager.py version  <file>  [--reason "why"]
    python3 version_manager.py rollback <file>  [--timestamp 2026-02-18T14-30-00]
    python3 version_manager.py list     <file>
    python3 version_manager.py log      [--last N]

Design:
    - All backups stored under PROJECT_ROOT/.versions/ mirroring original paths
    - Timestamped filenames: name__YYYY-MM-DDTHH-MM-SS.ext
    - versions.log is an append-only audit trail
    - Pure stdlib, no external dependencies
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Project root = parent of the directory this script lives in (system/)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
VERSIONS_DIR = PROJECT_ROOT / ".versions"
LOG_FILE = VERSIONS_DIR / "versions.log"


def _ensure_dirs():
    """Create .versions/ and log file if needed."""
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        LOG_FILE.touch()


def _timestamp() -> str:
    """ISO-style timestamp safe for filenames."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")


def _backup_path(original: Path, ts: str) -> Path:
    """
    Build the backup path mirroring original's location under .versions/.

    Example:
        original = PROJECT_ROOT/system/studies.json
        result   = PROJECT_ROOT/.versions/system/studies__2026-02-18T14-30-00.json
    """
    try:
        rel = original.resolve().relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        # File outside project — flatten into .versions/external/
        rel = Path("external") / original.name

    stem = rel.stem
    suffix = rel.suffix
    parent = VERSIONS_DIR / rel.parent
    parent.mkdir(parents=True, exist_ok=True)
    return parent / f"{stem}__{ts}{suffix}"


def _log_entry(action: str, original: str, backup: str, reason: str = ""):
    """Append one line to versions.log."""
    _ensure_dirs()
    ts = datetime.now(timezone.utc).isoformat()
    entry = json.dumps({
        "timestamp": ts,
        "action": action,
        "original": original,
        "backup": backup,
        "reason": reason,
    })
    with open(LOG_FILE, "a") as f:
        f.write(entry + "\n")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def version_file(filepath, reason: str = "") -> Path:
    """
    Create a timestamped backup of *filepath* before it is modified.

    Parameters
    ----------
    filepath : str or Path
        The file to back up (must exist).
    reason : str, optional
        Human-readable note recorded in the log.

    Returns
    -------
    Path  — the backup file location.

    Raises
    ------
    FileNotFoundError  if the source file does not exist.
    """
    _ensure_dirs()
    src = Path(filepath).resolve()
    if not src.exists():
        raise FileNotFoundError(f"Cannot version — file not found: {src}")

    ts = _timestamp()
    dst = _backup_path(src, ts)
    shutil.copy2(src, dst)  # preserves metadata

    _log_entry("version", str(src), str(dst), reason)
    print(f"  ✓ versioned → {dst.relative_to(PROJECT_ROOT)}")
    return dst


def list_versions(filepath) -> list[dict]:
    """
    Return all known versions of *filepath*, newest first.

    Each entry: {"timestamp": str, "backup": Path, "reason": str}
    """
    _ensure_dirs()
    src = str(Path(filepath).resolve())
    versions = []
    if LOG_FILE.exists():
        for line in LOG_FILE.read_text().splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("original") == src and entry.get("action") == "version":
                versions.append({
                    "timestamp": entry["timestamp"],
                    "backup": Path(entry["backup"]),
                    "reason": entry.get("reason", ""),
                })
    versions.sort(key=lambda v: v["timestamp"], reverse=True)
    return versions


def rollback(filepath, timestamp: str | None = None) -> Path:
    """
    Restore *filepath* from a backup.

    Parameters
    ----------
    filepath : str or Path
        The file to restore.
    timestamp : str, optional
        If provided, restore the version matching this timestamp substring.
        If omitted, restore the most recent version.

    Returns
    -------
    Path — the backup that was restored from.

    Raises
    ------
    ValueError  if no matching version is found.
    """
    versions = list_versions(filepath)
    if not versions:
        raise ValueError(f"No versions found for {filepath}")

    if timestamp:
        match = [v for v in versions if timestamp in v["timestamp"] or timestamp in str(v["backup"])]
        if not match:
            raise ValueError(f"No version matching '{timestamp}' for {filepath}")
        chosen = match[0]
    else:
        chosen = versions[0]

    backup_src = chosen["backup"]
    if not backup_src.exists():
        raise FileNotFoundError(f"Backup file missing: {backup_src}")

    target = Path(filepath).resolve()

    # Version the *current* state before overwriting (safety net)
    if target.exists():
        version_file(target, reason=f"pre-rollback safety snapshot")

    shutil.copy2(backup_src, target)
    _log_entry("rollback", str(target), str(backup_src),
               f"restored from {chosen['timestamp']}")
    print(f"  ✓ rolled back → {chosen['timestamp']}")
    return backup_src


def read_log(last: int = 0) -> list[dict]:
    """Read the full log, optionally limited to the last N entries."""
    _ensure_dirs()
    entries = []
    if LOG_FILE.exists():
        for line in LOG_FILE.read_text().splitlines():
            if line.strip():
                entries.append(json.loads(line))
    if last > 0:
        entries = entries[-last:]
    return entries


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="LongevityPath file versioning system")
    sub = parser.add_subparsers(dest="command")

    # version
    p_ver = sub.add_parser("version", help="Create a backup before editing")
    p_ver.add_argument("file", help="File to version")
    p_ver.add_argument("--reason", default="", help="Why this version is saved")

    # rollback
    p_rb = sub.add_parser("rollback", help="Restore from a backup")
    p_rb.add_argument("file", help="File to restore")
    p_rb.add_argument("--timestamp", default=None,
                       help="Timestamp substring to match (default: latest)")

    # list
    p_ls = sub.add_parser("list", help="List all versions of a file")
    p_ls.add_argument("file", help="File to list versions for")

    # log
    p_log = sub.add_parser("log", help="Show the version log")
    p_log.add_argument("--last", type=int, default=0,
                        help="Show only last N entries")

    args = parser.parse_args()

    if args.command == "version":
        version_file(args.file, reason=args.reason)

    elif args.command == "rollback":
        rollback(args.file, timestamp=args.timestamp)

    elif args.command == "list":
        versions = list_versions(args.file)
        if not versions:
            print("No versions found.")
        else:
            print(f"Versions of {args.file} ({len(versions)} total):\n")
            for v in versions:
                reason = f'  — {v["reason"]}' if v["reason"] else ""
                print(f"  {v['timestamp']}{reason}")
                print(f"    {v['backup']}")

    elif args.command == "log":
        entries = read_log(last=args.last)
        if not entries:
            print("Log is empty.")
        else:
            for e in entries:
                reason = f'  — {e.get("reason", "")}' if e.get("reason") else ""
                print(f"  [{e['action']:>8}]  {e['timestamp']}{reason}")
                print(f"            {Path(e['original']).name} → {Path(e['backup']).name}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
