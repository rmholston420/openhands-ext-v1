# ADR-0020 — UFW rule for docker-bridge → host required for OpenHands sandbox spawn

**Status:** Ratified
**Lock-in phase:** Phase 1 (full-suite smoke prerequisite)
**Supersedes:** —

## Context

`docker.openhands.dev/openhands/openhands:latest` (v1.11.0 app_server) spawns per-conversation sandbox containers (`ghcr.io/openhands/agent-server:1.36.0-python`) on the default `bridge` network. On Colossus, `POST /api/v1/app-conversations/stream-start` created the child sandbox successfully (container `Up`, its own uvicorn served `Application startup complete` in <1s), but the parent openhands-app marked the start-task ERROR with `Sandbox entered error state` ~15s later.

Root cause identified by reading `/app/openhands/app_server/sandbox/docker_sandbox_service.py`:
- `_container_to_checked_sandbox_info` polls the sandbox `AGENT_SERVER` exposed URL via `httpx_client.get(...)`.
- The URL is rewritten by `replace_localhost_hostname_for_docker` to `http://host.docker.internal:<published_port>/alive`.
- If the check fails past `STARTUP_GRACE_SECONDS = 15`, status is set to `ERROR`.

Direct network probes from the openhands-app container confirmed the failure was firewall-level, not container-level:
- `openhands-app → 172.17.0.4:8000` (child sandbox internal IP) → 200 in 2 ms.
- `openhands-app → host.docker.internal:<published_port>` → **5 s timeout**.
- `openhands-app → host.docker.internal:3000` (its own published port) → **5 s timeout**.
- `openhands-app → 172.17.0.1:8100` (host docker0 IP, coder) → **5 s timeout**.

Colossus UFW default INPUT policy is DROP. Docker bridge subnet `172.17.0.0/16` was not on the allow-list except for a few explicit ports (11434, 8000). Any packet from a bridge-container to a host-published port that wasn't explicitly whitelisted hit UFW and was dropped.

## Decision

**Add UFW rule allowing the docker default bridge subnet to reach host services**, as a documented Phase-1 prerequisite:

```bash
sudo ufw allow from 172.17.0.0/16 to any
```

This is required for:
1. openhands-app → sandbox healthcheck (`host.docker.internal:<published_port>/alive`).
2. Sandbox → coder@8100 (LLM traffic).
3. Sandbox → embedder@8090 (RAG traffic when enabled).

## Alternatives considered

- **`--network host` for openhands-app.** Sidesteps UFW but breaks the Phase 1 isolation model (openhands-app was intentionally on a per-conversation isolated mount to avoid touching `~/.openhands`). Also unnecessarily gives it full host network access when the actual need is narrow.
- **Per-port UFW rules for each sandbox published port.** Sandbox ports are ephemeral (docker assigns random high ports on each start). Cannot pre-allow. Rejected.
- **Custom docker network with fixed subnet + explicit allow-list.** Would work but adds daemon-config surface area. Rejected — 172.17.0.0/16 is stable per-host and single-purpose.
- **Configure openhands-app to poll the sandbox via internal bridge IP directly** (bypassing `replace_localhost_hostname_for_docker`). Would require patching upstream openhands or an env override that doesn't exist. Rejected — upstream drift risk.

## Rationale

- Colossus is single-user, local-first (per project instructions). The `172.17.0.0/16` subnet is entirely under Docker's control; allowing it to reach the host does not expand the external attack surface.
- Rule is idempotent, one line, survives reboot (UFW persists rules).
- Matches Docker's own recommended pattern for Linux hosts with UFW enabled — the widely-known `UFW-DOCKER` interaction issue.

## Consequences

- All bridge-network containers (openhands-app, sandbox children, kosmos-valkey, kosmos-adr010-searxng) can now reach any host port.
- Any non-Docker firewall-protected service on the host is now reachable from bridge containers. On Colossus this is acceptable because bridge containers are all locally-launched.
- Phase 1 smoke prerequisites now include a UFW check; encoded in `tests/smoke/README.md`.
- No BUILD_LOG entry required as a "port" but IS required as a step (see BUILD_LOG 2026-08-11 08:11 EDT).

## Verification

Post-fix (2026-08-11 08:12 EDT):
- `openhands-app → host.docker.internal:8100/v1/models` → 200 in 1.1 ms.
- `openhands-app → host.docker.internal:3000/health` → 200 in 1.7 ms.
- Full-suite smoke v3: **5/5 PASS**, T4 delta = 18113 prompt tokens, T5 event_count = 20.

## Lock-in phase

Phase 1 — full-suite smoke prerequisite. Documented in `tests/smoke/README.md`.

## References

- `tests/smoke/test_openhands_suite_v3.py`
- `tests/smoke/README.md`
- `DEBUG_LOG.md` (2026-08-11 08:11 EDT entry)
- `BUILD_LOG.md` (2026-08-11 08:12 EDT entry)
- Upstream: `/app/openhands/app_server/sandbox/docker_sandbox_service.py` (v1.11.0 app_server, image `docker.openhands.dev/openhands/openhands:latest`)
