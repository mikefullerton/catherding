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


def test_dirty_from_this_session_blocks(hook_local_repo, tmp_path):
    """File dirty on disk AND referenced by a Write in the transcript →
    this-session dirt → block as today."""
    target = hook_local_repo / "new.py"
    target.write_text("print('hi')\n")

    tp = _write_transcript(tmp_path, [
        {"name": "Write", "input": {"file_path": str(target)}},
    ])

    out, err, rc = _invoke_hook(hook_local_repo, tp)
    assert rc == 0
    d = _decision(out)
    assert d is not None and d.get("decision") == "block"
    assert "new.py" in d.get("reason", "")


def test_mixed_blocks_and_warns(hook_local_repo, tmp_path):
    """One file this session, one from prior session → block on the
    this-session path AND warn about the prior-session path."""
    mine = hook_local_repo / "mine.py"
    mine.write_text("new\n")
    theirs = hook_local_repo / "theirs.txt"
    theirs.write_text("old\n")

    tp = _write_transcript(tmp_path, [
        {"name": "Write", "input": {"file_path": str(mine)}},
    ])

    out, err, rc = _invoke_hook(hook_local_repo, tp)
    assert rc == 0
    d = _decision(out)
    assert d is not None and d.get("decision") == "block"
    assert "mine.py" in d.get("reason", "")
    assert "theirs.txt" not in d.get("reason", ""), \
        "prior-session path must not be in block reason"
    assert "theirs.txt" in err


def test_untracked_from_bash_redirect_blocks(hook_local_repo, tmp_path):
    """An untracked file whose path appears as a substring in a Bash
    command (e.g. `python foo.py > out.json`) counts as this-session
    via the conservative Bash substring match — block."""
    (hook_local_repo / "out.json").write_text('{"ok": true}\n')

    tp = _write_transcript(tmp_path, [
        {"name": "Bash", "input": {"command": "python foo.py > out.json"}},
    ])

    out, err, rc = _invoke_hook(hook_local_repo, tp)
    assert rc == 0
    d = _decision(out)
    assert d is not None and d.get("decision") == "block"
    assert "out.json" in d.get("reason", "")


def test_missing_transcript_fails_closed(hook_local_repo, tmp_path):
    """No transcript_path → treat all dirty as this-session → block."""
    (hook_local_repo / "x.txt").write_text("x\n")

    out, err, rc = _invoke_hook(hook_local_repo, transcript_path=None)
    assert rc == 0
    d = _decision(out)
    assert d is not None and d.get("decision") == "block", (
        f"expected block when transcript missing; out={out!r} err={err!r}"
    )
    assert "x.txt" in d.get("reason", "")


def test_malformed_transcript_fails_closed(hook_local_repo, tmp_path):
    """Transcript exists but has bad JSON → classification disabled →
    block on every dirty path (preserves old behavior on errors)."""
    (hook_local_repo / "y.txt").write_text("y\n")
    bad = tmp_path / "bad.jsonl"
    bad.write_text("not valid json at all\n")

    out, err, rc = _invoke_hook(hook_local_repo, bad)
    assert rc == 0
    d = _decision(out)
    assert d is not None and d.get("decision") == "block"
    assert "y.txt" in d.get("reason", "")
