"""Non-mutating, repository-local onboarding and publication checks."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def check():
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["github_repo"] == "SHIKI1255/personal-calendar", "Wrong target repository"
    assert manifest["default_branch"] == "main", "Unexpected branch policy"
    assert manifest["phase"] == "apple_badge_probe", "Compatibility gate requires review"
    assert manifest["device_acceptance"] == "pending", "Do not invent device acceptance"
    assert manifest["automatic_cleanup"] is False
    for filename in ("AGENTS.md", "local_task_preflight_profile.yaml", "LICENSE", "README.md"):
        assert (ROOT / filename).is_file(), "Missing control: " + filename
    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        assert not path.is_symlink(), "Unexpected symlink: " + str(path)
    workflows = ROOT / ".github/workflows"
    for path in workflows.glob("*.yml"):
        content = path.read_text(encoding="utf-8")
        assert "schedule:" not in content, "Scheduled updates require device acceptance first"
        assert "pull_request_target" not in content, "Untrusted code must not receive write tokens"
    result = subprocess.run(["git", "--no-optional-locks", "rev-parse", "--show-toplevel"], cwd=ROOT,
                            capture_output=True, text=True, check=True)
    assert Path(result.stdout.strip()).resolve() == ROOT, "Unexpected Git root"
    branch = subprocess.run(["git", "--no-optional-locks", "branch", "--show-current"], cwd=ROOT,
                            capture_output=True, text=True, check=True).stdout.strip()
    # Pull-request CI may use a detached checkout; local publication requires main.
    if branch:
        assert branch == "main", "Unexpected local publication branch"
    remotes = subprocess.run(["git", "--no-optional-locks", "remote", "get-url", "origin"], cwd=ROOT,
                             capture_output=True, text=True)
    if remotes.returncode == 0:
        remote = remotes.stdout.strip().lower().removesuffix(".git")
        assert remote in ("https://github.com/shiki1255/personal-calendar", "git@github.com:shiki1255/personal-calendar"), "Wrong origin"
    print("Local onboarding and publication controls: PASS; device acceptance: PENDING")


if __name__ == "__main__":
    check()
