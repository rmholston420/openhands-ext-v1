#!/usr/bin/env bash
# scripts/patch-cuda-headers.sh
#
# Idempotently patches the CUDA math_functions.h header to declare rsqrt
# and rsqrtf with `noexcept(true)` — matching Ubuntu 26.04 glibc 2.43's
# prototypes in /usr/include/x86_64-linux-gnu/bits/mathcalls.h.
#
# Why: CUDA (both 12.8 and 13.0.88 as installed on Colossus) declares
#   extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ double rsqrt(double x);
#   extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ float rsqrtf(float x);
# but glibc 2.42+ declares
#   extern double rsqrt (double __x) noexcept (true);
#   extern float rsqrtf (float __x) noexcept (true);
# and `cudafe++` treats the exception-specification mismatch as a hard
# error under C++17. This blocks compilation of *any* CUDA source that
# includes both cuda_runtime.h and the glibc math headers — including
# llama.cpp's CMake CUDA-compiler-identification probe, which fails
# before any real source is touched.
#
# Fix: patch the CUDA header to add `noexcept(true)` to those two lines.
# Sources for this approach:
#   - llama.cpp docs/build.md — "Fixing Compatibility Issues with Old
#     CUDA and New glibc"
#   - joanbm gist: fix-cuda-10.2-for-glibc-2.42
#
# We use `#if defined(__GLIBC__) && __GLIBC__ == 2 && __GLIBC_MINOR__ >= 42`
# guards so the patched header still works on distros with older glibc.
#
# CUDA 13.0.88 on Colossus has ONLY rsqrt/rsqrtf mismatches (cospi/sinpi
# were fixed in CUDA 13). CUDA 12.8 has all six. This script handles
# both.
#
# Idempotent: detects a marker line inserted on first run and no-ops
# thereafter. Also backs up the untouched header to `<header>.orig` on
# first run so it can be restored.
#
# Env:
#   CUDA_ROOT   default /usr/local/cuda-13.0
#   DRY_RUN=1   print planned diff without writing

set -euo pipefail

CUDA_ROOT="${CUDA_ROOT:-/usr/local/cuda-13.0}"
HEADER="$CUDA_ROOT/targets/x86_64-linux/include/crt/math_functions.h"
MARKER="// PATCHED-openhands-ext-v1-glibc242-noexcept"

if [ ! -f "$HEADER" ]; then
  echo "FAIL: header not found: $HEADER" >&2
  exit 1
fi

if grep -qF "$MARKER" "$HEADER"; then
  # Idempotent path. Also enforce 0644 in case an earlier version of this
  # script left the file 0600 root:root (as it did on Colossus 2026-08-11).
  CUR_MODE="$(stat -c '%a' "$HEADER" 2>/dev/null || echo)"
  if [ "$CUR_MODE" != "644" ]; then
    if [ -w "$HEADER" ] || [ "$(id -u)" = "0" ]; then
      chmod 0644 "$HEADER"
      echo "[fix] corrected mode on already-patched header to 0644"
    else
      echo "[warn] $HEADER is patched but has mode $CUR_MODE; re-run with sudo to correct." >&2
    fi
  fi
  echo "[ok] $HEADER already patched (marker present; mode $(stat -c '%a %U:%G' "$HEADER" 2>/dev/null || echo unknown))"
  exit 0
fi

# Preflight: check we can write it (sudo if needed).
if [ ! -w "$HEADER" ]; then
  echo "FAIL: no write permission on $HEADER" >&2
  echo "" >&2
  echo "Re-run with:  sudo -E bash scripts/patch-cuda-headers.sh" >&2
  exit 1
fi

# Back up on first patch
BACKUP="$HEADER.orig"
if [ ! -f "$BACKUP" ]; then
  cp -a "$HEADER" "$BACKUP"
  echo "[ok] backed up original to $BACKUP"
fi

# Preserve original mode and owner so post-swap file is still world-readable.
# CUDA headers are conventionally 0644 root:root. `stat` output format differs
# between distros; fall back to a hardcoded default if it parses oddly.
ORIG_MODE="$(stat -c '%a' "$HEADER" 2>/dev/null || echo 644)"
ORIG_OWNER="$(stat -c '%u:%g' "$HEADER" 2>/dev/null || echo 0:0)"
[ -z "$ORIG_MODE" ] && ORIG_MODE=644
[ -z "$ORIG_OWNER" ] && ORIG_OWNER=0:0

# Build patched file in a tempfile in the SAME directory as the target so `mv`
# is atomic (same filesystem) and doesn't fall back to copy+delete. Also lets
# us preserve permissions cleanly.
TMPDIR_HDR="$(dirname "$HEADER")"
TMP="$(mktemp "$TMPDIR_HDR/.math_functions.h.patched.XXXXXX")"
trap "rm -f '$TMP'" EXIT

# Two patterns to fix. Each declaration is a single line of the form:
#   extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ double rsqrt(double x);
# with optional __cdecl on some CUDA versions.
#
# Strategy: prefix each match with the marker as a comment on the same
# line so we can detect idempotency; wrap the modified declaration in
# a #if guard so older-glibc builds are unaffected.
#
# We do this with awk (not sed) to reliably wrap the line with #if/#else/
# #endif guards.

awk -v MARKER="$MARKER" '
  # Match the two exact declarations we need to fix.
  /^extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ double[[:space:]]+rsqrt[[:space:]]*\(double[[:space:]]+x\)[[:space:]]*;/ {
    print "#if defined(__GLIBC__) && __GLIBC__ == 2 && __GLIBC_MINOR__ >= 42 " MARKER
    line = $0
    sub(/;[[:space:]]*$/, " noexcept (true);", line)
    print line
    print "#else"
    print $0
    print "#endif"
    next
  }
  /^extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ float[[:space:]]+rsqrtf[[:space:]]*\(float[[:space:]]+x\)[[:space:]]*;/ {
    print "#if defined(__GLIBC__) && __GLIBC__ == 2 && __GLIBC_MINOR__ >= 42 " MARKER
    line = $0
    sub(/;[[:space:]]*$/, " noexcept (true);", line)
    print line
    print "#else"
    print $0
    print "#endif"
    next
  }
  # Also handle cospi/sinpi if they still exist (needed for CUDA 12.8;
  # harmless no-op on CUDA 13.0 where those decls already carry noexcept
  # via glibc-compatibility header updates).
  /^extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ double[[:space:]]+cospi[[:space:]]*\(double[[:space:]]+x\)[[:space:]]*;/ {
    print "#if defined(__GLIBC__) && __GLIBC__ == 2 && __GLIBC_MINOR__ >= 41 " MARKER
    line = $0
    sub(/;[[:space:]]*$/, " noexcept (true);", line)
    print line
    print "#else"
    print $0
    print "#endif"
    next
  }
  /^extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ float[[:space:]]+cospif[[:space:]]*\(float[[:space:]]+x\)[[:space:]]*;/ {
    print "#if defined(__GLIBC__) && __GLIBC__ == 2 && __GLIBC_MINOR__ >= 41 " MARKER
    line = $0
    sub(/;[[:space:]]*$/, " noexcept (true);", line)
    print line
    print "#else"
    print $0
    print "#endif"
    next
  }
  /^extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ double[[:space:]]+sinpi[[:space:]]*\(double[[:space:]]+x\)[[:space:]]*;/ {
    print "#if defined(__GLIBC__) && __GLIBC__ == 2 && __GLIBC_MINOR__ >= 41 " MARKER
    line = $0
    sub(/;[[:space:]]*$/, " noexcept (true);", line)
    print line
    print "#else"
    print $0
    print "#endif"
    next
  }
  /^extern __DEVICE_FUNCTIONS_DECL__ __device_builtin__ float[[:space:]]+sinpif[[:space:]]*\(float[[:space:]]+x\)[[:space:]]*;/ {
    print "#if defined(__GLIBC__) && __GLIBC__ == 2 && __GLIBC_MINOR__ >= 41 " MARKER
    line = $0
    sub(/;[[:space:]]*$/, " noexcept (true);", line)
    print line
    print "#else"
    print $0
    print "#endif"
    next
  }
  { print }
' "$HEADER" > "$TMP"

# Sanity: file must have grown (added #if/#else/#endif lines) AND still
# be a valid-looking C header (contains #ifndef guard etc.).
ORIG_LINES=$(wc -l < "$HEADER")
NEW_LINES=$(wc -l < "$TMP")
if [ "$NEW_LINES" -le "$ORIG_LINES" ]; then
  echo "FAIL: awk produced no patch (original $ORIG_LINES lines, new $NEW_LINES). Header may have unexpected format." >&2
  echo "Inspect: $HEADER" >&2
  rm -f "$TMP"
  exit 1
fi
if ! grep -q "$MARKER" "$TMP"; then
  echo "FAIL: marker not written by awk. Patch skipped." >&2
  rm -f "$TMP"
  exit 1
fi

if [ "${DRY_RUN:-0}" = "1" ]; then
  echo "--- dry run: diff of planned patch ---"
  diff "$HEADER" "$TMP" | head -80 || true
  echo "(dry run — not writing)"
  exit 0
fi

# Restore original mode + owner on the temp file BEFORE the atomic swap,
# so cmake / nvcc / any non-root user can still read the header.
chmod "$ORIG_MODE" "$TMP"
chown "$ORIG_OWNER" "$TMP" 2>/dev/null || true

# Atomic swap (same directory, same filesystem, preserves inode discipline)
mv "$TMP" "$HEADER"
trap - EXIT

# Defensive: enforce 0644 on the swapped-in file in case the mv path
# somehow reset perms (some FS/mount combos do).
chmod 0644 "$HEADER"

echo "[ok] patched $HEADER (backup: $BACKUP; mode $(stat -c '%a %U:%G' "$HEADER" 2>/dev/null || echo unknown))"

# Verify with a COMPILE-ONLY probe if nvcc is available at this CUDA_ROOT.
# We use -c (no link) because linking a bare __global__ program via nvcc
# without an explicit -lstdc++ can produce false-negative link errors on
# some distros; those errors are unrelated to the header patch we're
# validating. The header conflict manifests during cudafe++ parse, which
# `-c` fully exercises.
if [ -x "$CUDA_ROOT/bin/nvcc" ]; then
  PROBE_DIR="$(mktemp -d)"
  cat > "$PROBE_DIR/probe.cu" <<'CU'
#include <cuda_runtime.h>
#include <cmath>
__global__ void k() {}
CU
  # Run as the invoking user (not root) so we also confirm the patched header
  # is world-readable. If we're already root, drop to SUDO_USER when possible.
  PROBE_CMD=("$CUDA_ROOT/bin/nvcc" -ccbin=/usr/bin/gcc-13 -arch=sm_120 -c
             "$PROBE_DIR/probe.cu" -o "$PROBE_DIR/probe.o")
  if [ "$(id -u)" = "0" ] && [ -n "${SUDO_USER:-}" ]; then
    chown -R "$SUDO_USER" "$PROBE_DIR"
    if sudo -u "$SUDO_USER" "${PROBE_CMD[@]}" >/dev/null 2>&1; then
      echo "[ok] post-patch nvcc probe parsed clean (as $SUDO_USER)"
    else
      echo "[warn] post-patch nvcc probe failed — verbose output follows:" >&2
      sudo -u "$SUDO_USER" "${PROBE_CMD[@]}" 2>&1 | tail -40 >&2 || true
    fi
  else
    if "${PROBE_CMD[@]}" >/dev/null 2>&1; then
      echo "[ok] post-patch nvcc probe parsed clean"
    else
      echo "[warn] post-patch nvcc probe failed — verbose output follows:" >&2
      "${PROBE_CMD[@]}" 2>&1 | tail -40 >&2 || true
    fi
  fi
  rm -rf "$PROBE_DIR"
fi
