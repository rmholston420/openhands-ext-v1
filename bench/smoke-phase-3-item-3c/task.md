# Phase 3 Sign-Off Item 3.c — Trivial Task under DockerWorkspace

## Scope

Rerun the Row-1 trivial task, but backed by `DockerWorkspace` instead
of `LocalWorkspace`. Spec Phase 1 says the workspace policy is
`DockerWorkspace` only (v16 §1); Row-1 used `LocalWorkspace` for
initial mechanism verification. This closes the workspace-policy gap.

## SDK 1.41 workspace surface (verified from Colossus disk)

- `openhands.sdk.workspace`: `LocalWorkspace`, `RemoteWorkspace`,
  `AsyncRemoteWorkspace`, `Workspace` (union), `workspace` (module).
- `openhands.workspace.docker.workspace.DockerWorkspace`:
  subclass of `RemoteWorkspace`. Context-manager. Constructor fields:
  `server_image` (default `ghcr.io/openhands/agent-server:latest-python`),
  `host_port` (auto), `working_dir` (`/workspace`), `volumes`,
  `network` (Docker network name), `enable_gpu`,
  `health_check_timeout` (120 s), plus `forward_env`.
- `openhands.sdk.Conversation`: factory via `__new__` that dispatches
  on `workspace`: `LocalWorkspace` → `LocalConversation`,
  `RemoteWorkspace` → `RemoteConversation`. Same call site as Row-1.

## Configuration

- **Image:** `ghcr.io/openhands/agent-server:latest-python` (already
  cached on Colossus; SDK's own default). We do NOT pin to a specific
  version tag because none of the cached tags match SDK 1.41 exactly
  and `latest-python` is what the SDK ships as its default.
- **Networking:** `network="host"` so that the agent server inside the
  container can reach the coder at `http://127.0.0.1:8100/v1`
  unchanged, without `host.docker.internal` gymnastics on Linux.
- **GPU:** `enable_gpu=False`. The LLM runs outside the container.
- **Volumes:** none. The task creates its artifact in `/workspace`
  inside the container; we read the observation via the event stream,
  not from the host filesystem.
- **Health-check timeout:** default 120 s. `latest-python` is 3.93 GB
  and already local; startup should be well under that.

## Task

Same shape as Row-1, deliberately trivial and observable via events:

> In `/workspace`, create a file `hello.txt` whose only content is
> the string `docker-ok`. After you have created it, run `cat
> hello.txt` and finish.

## Pass criteria

- No exception raised during `DockerWorkspace.__enter__` /
  `Conversation.run()`.
- `Conversation.state.workspace` is a `RemoteWorkspace` instance
  (not `LocalWorkspace`).
- Container is created, becomes healthy, and is removed on exit.
- Event stream includes at least one `ActionEvent` that either
  (a) writes the file via a `str_replace_editor` / `file_editor` tool,
  or (b) uses `terminal` to `echo docker-ok > hello.txt` (and later a
  `cat`), and terminates with `FinishAction`.
- No `terminal_error` / `bash_command` error observations.
- Wall time under 300 s.

## Deferred to 3.d/3.e/3.f

- Canvas cloning, event-stream UI, confirmation-UI verification.
- These need Canvas running against `agent-server:8000`; 3.c only
  verifies the SDK-level Docker workspace mechanism.
