#!/usr/bin/env python3
"""
OpenHands sandbox reaper — 2026-08-11.

Removes docker containers matching `oh-agent-server-*` that are in a
stopped state (exited/dead/created). Never touches running containers.
Never touches openhands-app, vllm-*, embedder, or anything else.

Usage:
  sandbox_reaper.py                # reap once, silent unless changes
  sandbox_reaper.py --dry-run      # show what WOULD be reaped
  sandbox_reaper.py --verbose      # log every scan even when no-op
  sandbox_reaper.py --min-age-sec N  # skip stopped containers newer than N
                                     # seconds (safety window; default 60)

Exit codes:
  0 always (idempotent daemon-friendly). Errors go to stderr + log.

Installed as systemd-user oneshot + timer under:
  ~/.config/systemd/user/oh-sandbox-reaper.service
  ~/.config/systemd/user/oh-sandbox-reaper.timer
See systemd/README.md for install/uninstall commands.
"""
from __future__ import annotations

import argparse
import json
import logging
import logging.handlers
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

NAME_PATTERN = "oh-agent-server-"
LOG_PATH = Path.home() / ".forge-oh" / "sandbox-reaper.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

log = logging.getLogger("reaper")
log.setLevel(logging.INFO)
_h = logging.handlers.RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=3)
_h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
log.addHandler(_h)


def docker_ps_all():
    """Return list of dicts for ALL containers (running + stopped) matching pattern."""
    r = subprocess.run(
        ["docker", "ps", "-a", "--no-trunc",
         "--filter", f"name={NAME_PATTERN}",
         "--format", "{{json .}}"],
        capture_output=True, text=True, timeout=10,
    )
    if r.returncode != 0:
        log.error(f"docker ps failed: {r.stderr.strip()}")
        return []
    out = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line: continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            log.warning(f"skip malformed line: {e}")
    return out


def container_finished_at(cid: str):
    """FinishedAt for a container. Returns datetime or None if still running / unknown."""
    r = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.FinishedAt}}", cid],
        capture_output=True, text=True, timeout=5,
    )
    if r.returncode != 0:
        return None
    s = r.stdout.strip()
    if not s or s.startswith("0001-01-01"):
        return None
    try:
        if "." in s:
            head, tail = s.split(".", 1)
            frac = tail.rstrip("Z")[:6]
            s = f"{head}.{frac}+00:00"
        else:
            s = s.rstrip("Z") + "+00:00"
        return datetime.fromisoformat(s)
    except Exception as e:
        log.warning(f"parse FinishedAt '{s}': {e}")
        return None


def is_reapable(row: dict, min_age_sec: int) -> tuple[bool, str]:
    """Return (yes, reason)."""
    state = row.get("State", "").lower()
    name = row.get("Names", "") or row.get("Name", "")
    if not name.startswith(NAME_PATTERN):
        return False, f"skip (unexpected name: {name})"
    if state not in ("exited", "dead", "created"):
        return False, f"skip (state={state})"
    cid = row.get("ID") or row.get("Id") or ""
    fin = container_finished_at(cid) if state in ("exited", "dead") else None
    if fin is not None:
        age = (datetime.now(timezone.utc) - fin).total_seconds()
        if age < min_age_sec:
            return False, f"skip (stopped only {age:.0f}s ago, threshold {min_age_sec}s)"
        return True, f"reap (state={state}, stopped {age:.0f}s ago)"
    if state == "created":
        return True, "reap (state=created, never started)"
    return True, f"reap (state={state}, no FinishedAt)"


def reap(cid: str, name: str, dry_run: bool) -> bool:
    if dry_run:
        log.info(f"DRY-RUN would reap {name} ({cid[:12]})")
        return False
    r = subprocess.run(
        ["docker", "rm", "-f", cid],
        capture_output=True, text=True, timeout=15,
    )
    if r.returncode == 0:
        log.info(f"REAPED {name} ({cid[:12]})")
        return True
    log.error(f"reap FAILED {name} ({cid[:12]}): {r.stderr.strip()}")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--min-age-sec", type=int, default=60,
                    help="Only reap containers stopped at least this long ago (safety window)")
    args = ap.parse_args()

    containers = docker_ps_all()
    if not containers:
        if args.verbose:
            log.info(f"scan: 0 {NAME_PATTERN}* containers present")
        return 0

    reaped = 0
    skipped = 0
    for row in containers:
        ok, reason = is_reapable(row, args.min_age_sec)
        name = row.get("Names", "") or row.get("Name", "")
        cid = row.get("ID") or row.get("Id") or ""
        if ok:
            if reap(cid, name, args.dry_run):
                reaped += 1
        else:
            skipped += 1
            if args.verbose:
                log.info(f"{name}: {reason}")

    if reaped or args.verbose:
        log.info(f"scan complete: {reaped} reaped, {skipped} skipped, "
                 f"{len(containers)} total {NAME_PATTERN}* containers")

    if sys.stdout.isatty() or args.verbose or args.dry_run:
        print(f"scanned {len(containers)}  reaped {reaped}  skipped {skipped}  "
              f"(log: {LOG_PATH})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
