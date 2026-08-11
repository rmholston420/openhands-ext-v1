#!/usr/bin/env python3
"""V2: capture finish.message (report content), all str_replace/create writes,
and terminal output for smoke."""
import json, sys
from pathlib import Path

def dump(probe_path, out_path):
    d = json.loads(Path(probe_path).read_text())
    lines = []
    lines.append(f"# {probe_path}")
    lines.append(f"# role: {d.get('role')}")
    lines.append(f"# notes: {d.get('notes')}")
    lines.append("")
    for t in d['tasks']:
        tid = t['task_id']
        lines.append('=' * 80)
        lines.append(f"TASK: {tid}")
        lines.append(f"verdict={t['verdict']} source={t['verdict_source']} wall={t['wall_seconds']:.1f}s")
        lines.append('=' * 80)
        obj = json.loads(t['detail'])
        lines.append(f"turns={obj.get('turn_count')} cap={obj.get('hit_iteration_cap')} err={obj.get('agent_error_count')}")
        lines.append(f"mode={obj.get('expected_final_state_mode')}")
        lines.append(f"expected_seq={obj.get('expected_tool_sequence')}")
        lines.append(f"preferred={obj.get('preferred_tools')} dispreferred={obj.get('dispreferred_tools')}")
        re_ = obj.get('run_error')
        if re_:
            lines.append(f"run_error: {str(re_)[:300]}")
        sm = obj.get('smoke_result') or {}
        if sm:
            lines.append(f"smoke_exit={sm.get('exit_code')}")
            stdout = (sm.get('stdout') or '').strip()
            if stdout:
                lines.append(f"smoke_stdout: {stdout[:400]}")
        lines.append("")

        tt = obj.get('tool_trace') or []
        seq = [tc.get('tool') for tc in tt]
        lines.append(f"actual_seq ({len(seq)}): {seq}")
        finish_tc = next((tc for tc in tt if tc.get('tool') == 'finish'), None)
        lines.append(f"finish_present: {finish_tc is not None}")
        lines.append("")

        # FinishAction message — this is the report content for report-style tasks
        if finish_tc:
            msg = (finish_tc.get('args') or {}).get('message') or ''
            lines.append(f"--- FINISH.MESSAGE ({len(msg)} chars) ---")
            lines.append(msg[:4000])
            if len(msg) > 4000:
                lines.append("[TRUNCATED]")
            lines.append("")

        # All str_replace / create / write operations (actual code modifications)
        edits = []
        for tc in tt:
            if tc.get('tool') != 'file_editor':
                continue
            args = tc.get('args') or {}
            cmd = args.get('command') or ''
            path = args.get('path') or ''
            if cmd == 'create':
                content = args.get('file_text') or ''
                if content and content != 'None':
                    edits.append(('create', path, content))
            elif cmd == 'str_replace':
                old = args.get('old_str') or ''
                new = args.get('new_str') or ''
                if new and new != 'None':
                    edits.append(('str_replace', path, f"OLD:\n{old[:400]}\n---NEW:\n{new[:1500]}"))
            elif cmd == 'insert':
                new = args.get('new_str') or args.get('insert') or ''
                if new and new != 'None':
                    edits.append(('insert', path, new[:1500]))
        if edits:
            lines.append(f"--- FILE EDITS ({len(edits)}) ---")
            for op, path, content in edits:
                lines.append(f">>> {op} {path}")
                lines.append(content[:2500])
                if len(content) > 2500:
                    lines.append("[TRUNCATED]")
                lines.append("")
        lines.append("")
        lines.append("")

    Path(out_path).write_text('\n'.join(lines))
    return len('\n'.join(lines))

if __name__ == "__main__":
    for probe, out in [
        ("bench/scoring/full-coder/probes/awq.probe.json", "bench/scoring/full-coder/probes/awq_v2.txt"),
        ("bench/scoring/full-coder/probes/35b.probe.json", "bench/scoring/full-coder/probes/35b_v2.txt"),
    ]:
        n = dump(probe, out)
        print(f"{out}: {n} chars")
