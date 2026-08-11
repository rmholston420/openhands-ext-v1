# ADR-0004 — llama.cpp CUDA Toolchain Pin: CUDA 13.0 + gcc-13 + SM_120

**Status:** Ratified
**Lock-in phase:** Phase -1 (llama.cpp build)
**Supersedes:** —

## Context

Colossus runs Ubuntu 26.04 with glibc **2.43**. Both CUDA **12.8** and CUDA
**13.0** are installed side-by-side. The RTX 5090 (Blackwell) requires
compute capability **SM_120**, which is first supported in CUDA 12.8 and
also supported in 13.0.

On 2026-08-10, `scripts/build-llama-cpp.sh` targeting
`/usr/local/cuda-12.8` failed during the CMake compiler-identification step
with 6 errors of the form:

```
/usr/include/x86_64-linux-gnu/bits/mathcalls.h(83): error: exception
specification is incompatible with that of previous function "cospi"
(declared at line 2601 of
 /usr/local/cuda-12.8/bin/../targets/x86_64-linux/include/crt/math_functions.h)
```

for `cospi`, `sinpi`, `rsqrt` and their `f` variants. This is the
well-documented conflict between glibc ≥ 2.41 (which added `noexcept(true)`
to the double-precision math prototypes) and the CUDA 12.8 `crt/math_functions.h`
headers (which declare them without matching exception specifications).

CUDA 13.0 (`V13.0.88`, installed at `/usr/local/cuda-13.0`) has updated
headers that match glibc 2.43, and its `nvcc` accepts gcc-13/14/15 as a
host compiler. Blackwell SM_120 is fully supported.

## Decision

llama.cpp on Colossus is built with:

- **CUDA toolchain:** `/usr/local/cuda-13.0` (nvcc 13.0.88)
- **Host compiler:** `/usr/bin/gcc-13` (Ubuntu 13.4.0)
- **CUDA architecture:** `-DCMAKE_CUDA_ARCHITECTURES=120` (Blackwell)
- **CMake:** system cmake (≥ 4.2); Ninja generator
- **Env pinning:** `PATH`, `CUDA_PATH`, `LD_LIBRARY_PATH` prefixed with the
  cuda-13.0 tree before invoking cmake, so ptxas and cuBLAS lookups also
  see 13.0 rather than the 12.8 system default.
- **Flags:** `-DGGML_CUDA=ON -DLLAMA_CURL=ON -DCUDAToolkit_ROOT=$CUDA_ROOT`

CUDA 12.8 remains installed on Colossus for other consumers but is
**not used by any llama.cpp build in this repo**.

## Rationale

Alternatives considered:

1. **Keep CUDA 12.8, apply the `-D__CUDA_NO_HALF_CONVERSIONS__` /
   `-D_FORCE_INLINES` workaround.** Rejected — the specific glibc-2.43
   `noexcept` conflict is not fixed by those macros; it's a header-level
   prototype mismatch, not an inline-function issue. Real fixes involve
   patching CUDA 12.8's `crt/math_functions.h`, which we are not willing
   to do to a vendor-installed toolchain.

2. **Downgrade glibc / downgrade the host distro.** Rejected — user pinned
   Ubuntu 26.04 as the Colossus OS.

3. **Use CUDA 13.0.** Accepted. Both toolchains are already installed;
   switching costs one script edit; upstream llama.cpp actively supports
   CUDA 13.

4. **Match host compiler to CUDA 13's preferred gcc-14.** Deferred — gcc-13
   is currently installed and CUDA 13 accepts it. If a future CUDA 13.x
   release drops gcc-13 host support this ADR gets amended and gcc-14
   installed.

## Consequences

- `scripts/build-llama-cpp.sh` now points at `/usr/local/cuda-13.0` and
  prepends its bin/lib to the environment before configure.
- `PORTING_LEDGER.md` entry for llama.cpp gains a
  `Toolchain: CUDA 13.0 + gcc-13 + SM_120` line.
- vLLM installs a **separate** set of CUDA-13 wheel packages
  (`nvidia-cuda-nvcc==13.3.73`, `nvidia-cublas==13.1.1.3`, etc.) inside
  `.venv/`. Those wheels are independent of `/usr/local/cuda-13.0` and do
  not conflict.
- If we ever add a **CUDA-12-only** consumer to this repo we will file a
  new ADR to pin that consumer to 12.8; the two toolchains coexist by
  design.
- Any future build failure with the exact `mathcalls.h` `noexcept`
  signature reopens this ADR.

## Lock-in phase

Phase -1 (llama.cpp build). Applies to every subsequent phase that
consumes llama.cpp binaries.

## References

- `scripts/build-llama-cpp.sh`
- `DEBUG_LOG.md` entry 2026-08-11 (glibc-2.43 vs CUDA-12.8 `math_functions.h`)
- `BUILD_LOG.md` entry 2026-08-11 (corrective Phase -1 fixes)
- Upstream note: llama.cpp `docs/build.md` — CUDA build section
