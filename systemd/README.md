# systemd user units for openhands-ext-v1

## `oh-sandbox-reaper.{service,timer}`

Reaps stopped `oh-agent-server-*` docker containers (per-conversation OpenHands
sandboxes that stay around after the conversation ends). Runs
`scripts/sandbox_reaper.py`.

### What it reaps

- Container name must start with `oh-agent-server-`.
- Container state must be `exited`, `dead`, or `created`.
- If `exited`/`dead`, must have been stopped at least 60 s ago (safety window
  configurable via `--min-age-sec`).

### What it will NEVER touch

- Running containers (any state other than the three above).
- Anything not matching `oh-agent-server-*` — `openhands-app`, `vllm-*`,
  `embedder`, `vllm-bench`, etc. are all safe.

### Install (Colossus baseline, done 2026-08-11 08:35 EDT)

```bash
mkdir -p ~/.config/systemd/user
cp systemd/oh-sandbox-reaper.service ~/.config/systemd/user/
cp systemd/oh-sandbox-reaper.timer   ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now oh-sandbox-reaper.timer
```

If you want the timer to run when logged out:

```bash
sudo loginctl enable-linger $USER
```

(Already enabled on Colossus.)

### Inspect

```bash
# is the timer active + when does it next fire?
systemctl --user list-timers oh-sandbox-reaper.timer

# last-run status + recent journal
systemctl --user status oh-sandbox-reaper.service --no-pager
journalctl --user -u oh-sandbox-reaper.service -n 20 --no-pager

# per-run script log (rotates at 1MB, 3 backups)
tail -f ~/.forge-oh/sandbox-reaper.log
```

### Manual invocation

```bash
# preview only
python3 ~/dev/openhands-ext-v1/scripts/sandbox_reaper.py --dry-run --verbose

# force a run right now
systemctl --user start oh-sandbox-reaper.service

# one-shot ad hoc
python3 ~/dev/openhands-ext-v1/scripts/sandbox_reaper.py --verbose
```

### Disable / uninstall

```bash
systemctl --user disable --now oh-sandbox-reaper.timer
rm ~/.config/systemd/user/oh-sandbox-reaper.{service,timer}
systemctl --user daemon-reload
```

### Cadence

Timer fires every 5 minutes (`OnUnitActiveSec=5min`), first fire 2 min after
boot (`OnBootSec=2min`), ±30 s jitter (`AccuracySec=30s`). Change in the
`.timer` file, then `systemctl --user daemon-reload && systemctl --user restart oh-sandbox-reaper.timer`.
