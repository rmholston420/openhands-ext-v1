#!/usr/bin/env python3
"""Extract actual deliverables (file writes, terminal outputs) from probe JSONs
so we can score against gold for gate-3."""
import json, sys
from pathlib import Path

def dump(probe_path, out_path):
    d = json.loads(Path(probe_path).read_text())
    lines = []
    lines.append(f"# {probe_path}")
    lines.append(f"# role: {d.get('role')}  notes: {d.get('notes')}")
    lines.append("")
    for t in d['tasks']:
        tid = t['task_id']
        lines.append('=' * 76)
        lines.append(f"TASK: {tid}")
        lines.append(f"verdict={t['verdict']} source={t['verdict_source']} wall={t['wall_seconds']:.1f}s")
        lines.append('=' * 76)
        try:
            obj = json.loads(t['detail'])
        except Exception as e:
            lines.append(f"detail parse fail: {e}")
            continue
        lines.append(f"turn_count={obj.get('turn_count')} hit_iteration_cap={obj.get('hit_iteration_cap')} agent_error_count={obj.get('agent_error_count')}")
        lines.append(f"expected_final_state_mode={obj.get('expected_final_state_mode')}")
        lines.append(f"expected_tool_sequence={obj.get('expected_tool_sequence')}")
        lines.append(f"preferred_tools={obj.get('preferred_tools')}")
        lines.append(f"dispreferred_tools={obj.get('dispreferred_tools')}")
        re_ = obj.get('run_error')
        lines.append(f"run_error: {str(re_)[:400] if re_ else 'None'}")
        sm = obj.get('smoke_result') or {}
        if sm:
            lines.append(f"smoke_exit={sm.get('exit_code')}")
            stdout = sm.get('stdout') or ''
            stderr = sm.get('stderr') or ''
            if stdout:
                lines.append(f"smoke_stdout ({len(stdout)} chars):")
                lines.append(stdout[:2000])
            if stderr:
                lines.append(f"smoke_stderr ({len(stderr)} chars):")
                lines.append(stderr[:1000])
        lines.append("")

        tt = obj.get('tool_trace') or []
        seq = [tc.get('tool') for tc in tt]
        lines.append(f"actual_tool_sequence ({len(seq)}): {seq}")
        finish_seen = any('finish' in (tc.get('tool') or '').lower() for tc in tt)
        lines.append(f"finish_in_tools={finish_seen}")
        lines.append("")

        # Every file-editor write (create/str_replace/write) with content
        writes_by_path = {}  # path -> list of (cmd, content)
        for tc in tt:
            if tc.get('tool') != 'file_editor':
                continue
            args = tc.get('args') or {}
            cmd = args.get('command') or ''
            path = args.get('path') or ''
            if cmd in ('create', 'write', 'str_replace', 'insert'):
                content = args.get('file_text') or args.get('new_str') or args.get('insert') or ''
                if content and content != 'None':
                    writes_by_path.setdefault(path, []).append((cmd, content))
        for path, ops in writes_by_path.items():
            # Keep last write per path
            cmd, content = ops[-1]
            lines.append(f"--- LAST_WRITE {path} (cmd={cmd}, {len(content)} chars, {len(ops)} total ops) ---")
            lines.append(content[:6000])
            if len(content) > 6000:
                lines.append("[TRUNCATED]")
            lines.append("")

        # Terminal outputs — cat, pytest, python
        term_outs = []
        for tc in tt:
            if tc.get('tool') != 'terminal':
                continue
            args = tc.get('args') or {}
            cmd = args.get('command') or ''
            obs = tc.get('observation') or ''
            if cmd.startswith('cat ') or 'pytest' in cmd or 'python -m' in cmd or cmd.startswith('python '):
                term_outs.append((cmd, obs))
        if term_outs:
            lines.append(f"--- terminal outputs ({len(term_outs)}) ---")
            for cmd, obs in term_outs[-5:]:
                lines.append(f"$ {cmd[:120]}")
                lines.append((obs or '')[:1500])
                lines.append("")
        lines.append("")
        lines.append("")

    Path(out_path).write_text('\n'.join(lines))
    return len('\n'.join(lines))

if __name__ == "__main__":
    for probe, out in [
        ("bench/scoring/full-coder/probes/awq.probe.json", "bench/scoring/full-coder/probes/awq_deliverables.txt"),
        ("bench/scoring/full-coder/probes/35b.probe.json", "bench/scoring/full-coder/probes/35b_deliverables.txt"),
    ]:
        n = dump(probe, out)
        print(f"{out}: {n} chars")
