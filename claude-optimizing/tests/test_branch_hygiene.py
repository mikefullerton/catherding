import subprocess
from .conftest import run_cc


def test_no_problems(local_git_repo):
    out, err, rc = run_cc("cc-branch-hygiene", cwd=local_git_repo)
    assert rc == 0
    assert "clean" in out


def test_reports_merged_branch(local_git_repo):
    r = local_git_repo

    subprocess.run(["git", "-C", str(r), "checkout", "-b", "feature-x"],
                   check=True, capture_output=True)
    (r / "f.txt").write_text("x\n")
    subprocess.run(["git", "-C", str(r), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(r), "commit", "-m", "feature x"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(r), "checkout", "main"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(r), "merge", "--no-ff", "feature-x"],
                   check=True, capture_output=True)

    out, err, rc = run_cc("cc-branch-hygiene", cwd=r)
    assert rc == 0
    assert "feature-x" in out
    assert "merged" in out


def test_cleanup_deletes_merged_branch(local_git_repo):
    r = local_git_repo

    subprocess.run(["git", "-C", str(r), "checkout", "-b", "delete-me"],
                   check=True, capture_output=True)
    (r / "d.txt").write_text("d\n")
    subprocess.run(["git", "-C", str(r), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(r), "commit", "-m", "to delete"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(r), "checkout", "main"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(r), "merge", "--no-ff", "delete-me"],
                   check=True, capture_output=True)

    out, err, rc = run_cc("cc-branch-hygiene", ["--cleanup"], cwd=r)
    assert rc == 0
    assert "deleted" in out

    branches = subprocess.run(
        ["git", "-C", str(r), "branch"], capture_output=True, text=True,
    ).stdout
    assert "delete-me" not in branches


def test_not_a_git_repo(tmp_path):
    out, err, rc = run_cc("cc-branch-hygiene", cwd=tmp_path)
    assert rc != 0
    assert "not a git repo" in err
