"""Integration tests for session-aware Stop hook.

Invokes cc-repo-hygiene-hook.py as a subprocess with synthesized
transcripts and real local git repos (no GitHub required).
"""
import json
import subprocess
from pathlib import Path

HOOK_PATH = (
    Path(__file__).resolve().parent.parent / "scripts-hooks" / "cc-repo-hygiene-hook.py"
)


def _write_transcript(tmp_path, tool_uses):
    """Write a minimal JSONL transcript with the given tool_use entries.

    tool_uses: list of dicts like {"name": "Write", "input": {"file_path": "/x"}}.
    """
    path = tmp_path / "transcript.jsonl"
    with path.open("w") as f:
        for tu in tool_uses:
            block = {"type": "tool_use", **tu}
            f.write(json.dumps({"message": {"content": [block]}}) + "\n")
    return path


def _invoke_hook(cwd, transcript_path=None):
    payload = {"cwd": str(cwd), "stop_hook_active": False}
    if transcript_path is not None:
        payload["transcript_path"] = str(transcript_path)
    r = subprocess.run(
        [str(HOOK_PATH)],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=30,
    )
    return r.stdout, r.stderr, r.returncode


def _decision(stdout):
    stdout = stdout.strip()
    if not stdout:
        return None
    return json.loads(stdout)


def test_dirty_from_other_session_warns_not_blocks(hook_local_repo, tmp_path):
    """File dirty on disk, but the transcript doesn't reference it →
    treat as prior-session state, warn on stderr, allow Stop."""
    (hook_local_repo / "orphan.txt").write_text("from another session\n")

    tp = _write_transcript(tmp_path, [
        {"name": "Write", "input": {"file_path": str(hook_local_repo / "other.py")}},
    ])

    out, err, rc = _invoke_hook(hook_local_repo, tp)
    assert rc == 0
    assert _decision(out) is None, f"expected no block, got: {out!r}"
    assert "orphan.txt" in err, f"expected warning mentioning orphan.txt, got: {err!r}"
    assert "prior sessions" in err.lower()
