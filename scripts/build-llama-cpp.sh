#!/usr/bin/env bash
# scripts/build-llama-cpp.sh
#
# Clones and builds llama.cpp for RTX 5090 (Blackwell SM_120) on Colossus.
#
# Toolchain (from Colossus probe 2026-08-10 & 2026-08-10 23:59):
#   CUDA:   /usr/local/cuda-13.0  (nvcc 13.0.88)  <-- CUDA 12.8 is BROKEN
#                                                 on Ubuntu 26.04 glibc 2.43;
#                                                 see DEBUG_LOG.md.
#   Host:   /usr/bin/gcc-13       (CUDA 13 accepts gcc-13/14/15; gcc-13
#                                  chosen because it's currently the only
#                                  installed CUDA-supported host compiler.)
#   CMake:  /usr/bin/cmake
#   Ninja:  /usr/bin/ninja
#
# Build location: vendor/llama.cpp/  (gitignored via vendor/)
#
# Steps:
#   1. Re-fetch the top-of-releases tag from GitHub (spec §-1.1 rule:
#      NEVER hardcode; always re-fetch and log).
#   2. Clone or update the vendor tree at that tag.
#   3. cmake configure with CUDA 13.0 + SM_120 + gcc-13 host compiler.
#   4. ninja build (parallel).
#   5. Report binaries and version.
#
# Log: /tmp/openhands-ext-v1-build-llama-cpp-<timestamp>.log

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

LOG="/tmp/openhands-ext-v1-build-llama-cpp-$(date +%s).log"
echo "logging to $LOG"

VENDOR_DIR="$REPO_ROOT/vendor/llama.cpp"
CUDA_ROOT="/usr/local/cuda-13.0"
HOST_CC="/usr/bin/gcc-13"
HOST_CXX="/usr/bin/g++-13"
SM_ARCH="120"

{
  echo "===== build-llama-cpp start — $(date -Iseconds) ====="

  # 0. Preflight
  for tool in cmake ninja git curl jq "$HOST_CC" "$HOST_CXX" "$CUDA_ROOT/bin/nvcc"; do
    if [ ! -x "$tool" ] && ! command -v "$tool" >/dev/null 2>&1; then
      echo "FAIL: required tool missing: $tool" >&2
      exit 1
    fi
  done
  echo "[ok] preflight"
  echo "nvcc:   $($CUDA_ROOT/bin/nvcc --version | tail -1)"
  echo "gcc-13: $($HOST_CC --version | head -1)"
  echo "cmake:  $(cmake --version | head -1)"
  echo "ninja:  $(ninja --version)"
  echo "glibc:  $(ldd --version | head -1)"

  # 1. Re-fetch live tag
  echo ""
  echo "--- re-fetching llama.cpp latest release tag ---"
  LATEST_TAG="$(curl -sf https://api.github.com/repos/ggml-org/llama.cpp/releases/latest | jq -r .tag_name)"
  if [ -z "$LATEST_TAG" ] || [ "$LATEST_TAG" = "null" ]; then
    echo "FAIL: could not fetch latest tag from GitHub" >&2
    exit 1
  fi
  echo "latest tag: $LATEST_TAG"

  # 2. Clone or update
  mkdir -p "$REPO_ROOT/vendor"
  if [ ! -d "$VENDOR_DIR/.git" ]; then
    echo ""
    echo "--- cloning llama.cpp ---"
    git clone --depth 1 --branch "$LATEST_TAG" https://github.com/ggml-org/llama.cpp.git "$VENDOR_DIR"
  else
    echo ""
    echo "--- updating existing llama.cpp checkout ---"
    cd "$VENDOR_DIR"
    git fetch --tags --depth 1 origin "$LATEST_TAG" || \
      git fetch --tags origin "$LATEST_TAG"
    git checkout -f "$LATEST_TAG"
    cd "$REPO_ROOT"
  fi

  cd "$VENDOR_DIR"
  CHECKOUT_SHA="$(git rev-parse HEAD)"
  echo "checkout: $LATEST_TAG @ $CHECKOUT_SHA"

  # 3. Configure
  #
  # Point PATH at cuda-13.0 first so any child processes (e.g. cuBLAS
  # lookup, ptxas invocations by nvcc) also see the 13.0 toolchain, not the
  # 12.8 default installed on Colossus.
  export PATH="$CUDA_ROOT/bin:$PATH"
  export CUDA_PATH="$CUDA_ROOT"
  export LD_LIBRARY_PATH="$CUDA_ROOT/lib64:${LD_LIBRARY_PATH:-}"

  # 3.5. Patch CUDA math_functions.h for glibc 2.43 compatibility.
  # CUDA 13.0.88's rsqrt/rsqrtf decls omit `noexcept(true)` while glibc
  # 2.43 declares them WITH it; cudafe++ treats this as a hard error.
  # See DEBUG_LOG.md 2026-08-11 and scripts/patch-cuda-headers.sh.
  echo ""
  echo "--- patching CUDA headers (idempotent, requires sudo) ---"
  # Pass CUDA_ROOT explicitly via sudo's env preservation. `-E` is silently
  # dropped by strict sudoers configs (as it was on Colossus 2026-08-11), so
  # we use the `VAR=value command` form which sudo honors reliably.
  if [ -w "$CUDA_ROOT/targets/x86_64-linux/include/crt/math_functions.h" ]; then
    CUDA_ROOT="$CUDA_ROOT" bash "$REPO_ROOT/scripts/patch-cuda-headers.sh"
  else
    sudo CUDA_ROOT="$CUDA_ROOT" bash "$REPO_ROOT/scripts/patch-cuda-headers.sh"
  fi

  echo ""
  echo "--- cmake configure ---"
  rm -rf build
  cmake -B build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DGGML_CUDA=ON \
    -DCMAKE_CUDA_ARCHITECTURES="$SM_ARCH" \
    -DCMAKE_CUDA_COMPILER="$CUDA_ROOT/bin/nvcc" \
    -DCMAKE_CUDA_HOST_COMPILER="$HOST_CC" \
    -DCMAKE_C_COMPILER="$HOST_CC" \
    -DCMAKE_CXX_COMPILER="$HOST_CXX" \
    -DCUDAToolkit_ROOT="$CUDA_ROOT"

  # 4. Build
  echo ""
  echo "--- ninja build (parallel) ---"
  cmake --build build --config Release -j"$(nproc)"

  # 5. Report
  echo ""
  echo "--- built binaries ---"
  ls -la build/bin/ | head -30

  echo ""
  echo "--- llama-server sanity ---"
  ./build/bin/llama-server --version 2>&1 | head -5 || true

  # 6. Metadata
  mkdir -p "$REPO_ROOT/bench/results"
  METADATA_FILE="$REPO_ROOT/bench/results/phase-neg-1-build-llama-cpp-$(date -u +%Y%m%dT%H%M%SZ).json"
  cat > "$METADATA_FILE" <<JSON
{
  "phase": "-1",
  "component": "llama.cpp build",
  "status": "pass",
  "timestamp_utc": "$(date -u -Iseconds)",
  "tag": "$LATEST_TAG",
  "sha": "$CHECKOUT_SHA",
  "toolchain": {
    "cuda": "$($CUDA_ROOT/bin/nvcc --version | tail -1 | awk -F, '{print $NF}' | xargs)",
    "cuda_root": "$CUDA_ROOT",
    "host_compiler": "$($HOST_CC --version | head -1)",
    "sm_arch": "$SM_ARCH",
    "glibc": "$(ldd --version | head -1 | awk '{print $NF}')"
  },
  "server_binary": "$VENDOR_DIR/build/bin/llama-server"
}
JSON

  echo ""
  echo "recorded: $METADATA_FILE"
  echo ""
  echo "===== build-llama-cpp done — $(date -Iseconds) ====="
  echo "vendor: $VENDOR_DIR"
  echo "tag:    $LATEST_TAG"
  echo "SHA:    $CHECKOUT_SHA"
  echo "server: $VENDOR_DIR/build/bin/llama-server"
} 2>&1 | tee "$LOG"
