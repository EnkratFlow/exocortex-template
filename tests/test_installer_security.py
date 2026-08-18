#!/usr/bin/env python3
"""Focused fictional tests for installer public-boundary and ambient-env handling."""

from __future__ import annotations

import hashlib
import os
import shutil
import shlex
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


TEMPLATE = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()

PROTECTED_FILES = {
    "SESSION_CONTEXT.md",
    "SESSION_CONTEXT.md.backup",
    "SESSION_CONTEXT.local.md",
    "TODO.md",
    "LESSONS.md",
    "PROJECT_MEMORY.md",
    "OPEN_DECISIONS.md",
    "subconscious_patterns.md",
    ".project-name",
    ".install-manifest",
    ".hub_enabled",
    ".hub_disabled",
}
PROTECTED_PREFIXES = ("events/", "archive/", "hub/", "local/", "planning/", "work-items/")
PROTECTED_CONTROL = {
    "control/ACTIVE_WORK.md",
    "control/BRANCH_POLICY.md",
    "control/REPO_STATE.md",
    "control/EXECUTOR_REGISTRY.json",
    "control/EXTERNAL_SYNC_POLICY.json",
    "control/INTERRUPTS.md",
    "control/BACKLOG.md",
    "control/ROADMAP.md",
    "control/ARCH_OVERVIEW.md",
    "control/REPO_ORGANIZATION_REPORT.md",
}
DOWNSTREAM_IGNORED_DATA = tuple(
    sorted(f".exocortex/{relative}" for relative in PROTECTED_FILES | PROTECTED_CONTROL)
)


def run(
    *args: str,
    cwd: Path,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode:
        raise AssertionError(f"command failed: {args!r}: {result.stderr}")
    return result


def is_env_name(name: str) -> bool:
    return name == ".env" or name.startswith(".env.") or name == ".envrc"


def include_in_integrity(relative: str) -> bool:
    if relative == "SHA256SUMS":
        return False
    parts = Path(relative).parts
    if ".git" in parts or "__pycache__" in parts or relative.endswith((".pyc", ".pyo")):
        return False
    if is_env_name(Path(relative).name) and relative != ".exocortex/.env.example":
        return False
    if relative.startswith(".exocortex/"):
        value = relative[len(".exocortex/") :]
        if value in PROTECTED_FILES or value in PROTECTED_CONTROL:
            return False
        if value.startswith("SESSION_CONTEXT_BACKUP_") and value.endswith(".md") and "/" not in value:
            return False
        if value.startswith(PROTECTED_PREFIXES):
            return False
    return True


def copy_candidate(destination: Path) -> None:
    def ignored(directory: str, names: list[str]) -> set[str]:
        here = Path(directory).resolve().relative_to(TEMPLATE)
        denied: set[str] = set()
        for name in names:
            relative = (here / name).as_posix()
            if name in {".git", "__pycache__"} or relative.startswith(
                (".exocortex/local", ".exocortex/work-items")
            ) or relative in {
                ".exocortex/control/EXECUTOR_REGISTRY.json",
                ".exocortex/control/EXTERNAL_SYNC_POLICY.json",
            }:
                denied.add(name)
        return denied

    shutil.copytree(TEMPLATE, destination, ignore=ignored)


def regenerate_integrity(root: Path) -> None:
    files = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise AssertionError(f"fixture contains symlink: {path}")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            if include_in_integrity(relative):
                files.append((relative, path))
    files.sort()

    modes: dict[str, int] = {}
    for relative, path in files:
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode not in {0o644, 0o755}:
            mode = 0o755 if path.suffix in {".sh", ".py"} and os.access(path, os.X_OK) else 0o644
            path.chmod(mode)
        modes[relative] = mode
    modes["SHA256SUMS"] = 0o644
    (root / "FILEMODES").write_text(
        "".join(f"{modes[relative]:04o}  {relative}\n" for relative in sorted(modes)),
        encoding="utf-8",
    )

    checksum_files = []
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            relative = path.relative_to(root).as_posix()
            if include_in_integrity(relative):
                checksum_files.append((relative, path))
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}\n"
        for relative, path in sorted(checksum_files)
    ]
    (root / "SHA256SUMS").write_text("".join(lines), encoding="utf-8")


def install(source: Path, target: Path, *, force_tar: bool = False, canary: bool = False) -> subprocess.CompletedProcess[str]:
    fake_home = target.parent / f"{target.name}-home"
    fake_tmp = target.parent / f"{target.name}-tmp"
    fake_home.mkdir()
    fake_tmp.mkdir()
    digest = hashlib.sha256((source / "SHA256SUMS").read_bytes()).hexdigest()
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"),
        "HOME": str(fake_home),
        "TMPDIR": str(fake_tmp),
        "LC_ALL": "C",
        "LANG": "C",
        "EXOCORTEX_LOCAL_SOURCE": str(source),
        "EXOCORTEX_CANDIDATE_DIGEST": digest,
        "EXOCORTEX_FORCE_TAR_STAGE": "1" if force_tar else "0",
    }
    if canary:
        env["EXOCORTEX_AMBIENT_CANARY"] = "fictional-test-only"
    return run("bash", str(source / "install.sh"), "fixture", cwd=target, env=env, check=False)


def new_target(parent: Path, name: str) -> Path:
    target = parent / name
    target.mkdir()
    run("git", "init", "-q", cwd=target)
    return target


def safe_update_dry_run(
    source: Path, target: Path, backup: Path
) -> subprocess.CompletedProcess[str]:
    fake_home = target.parent / f"{backup.name}-home"
    fake_tmp = target.parent / f"{backup.name}-tmp"
    fake_home.mkdir()
    fake_tmp.mkdir()
    backup.mkdir()
    digest = hashlib.sha256((source / "SHA256SUMS").read_bytes()).hexdigest()
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"),
        "HOME": str(fake_home),
        "TMPDIR": str(fake_tmp),
        "LC_ALL": "C",
        "LANG": "C",
        "EXOCORTEX_AMBIENT_CANARY": "fictional-test-only",
    }
    return run(
        "bash",
        str(source / "scripts/safe-update.sh"),
        "--template",
        str(source),
        "--candidate-digest",
        digest,
        "--backup-dir",
        str(backup),
        "--dry-run",
        cwd=target,
        env=env,
        check=False,
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="exo-installer-security-") as raw:
        root = Path(raw)
        source = root / "source"
        copy_candidate(source)
        regenerate_integrity(source)

        clean_target = new_target(root, "clean-target")
        target_shadow_canary = root / "target-import-shadow-executed"
        target_shadow = clean_target / "hashlib.py"
        target_shadow.write_text(
            "from pathlib import Path\n"
            f"Path({str(target_shadow_canary)!r}).touch()\n"
            "raise RuntimeError('target import shadow executed')\n",
            encoding="utf-8",
        )
        clean = install(source, clean_target)
        assert clean.returncode == 0, clean.stderr
        assert (clean_target / "AI_START_HERE.md").is_file()
        assert target_shadow.is_file()
        assert not target_shadow_canary.exists(), "installer executed target Python shadow"
        for relative in DOWNSTREAM_IGNORED_DATA:
            ignored = run(
                "git", "check-ignore", "--no-index", "-q", "--", relative,
                cwd=clean_target, check=False,
            )
            assert ignored.returncode == 0, f"downstream data path is not ignored: {relative}"

        forbidden = source / ".exocortex/.env.production"
        forbidden.write_text("FICTIONAL_ENV_CANARY\n", encoding="utf-8")
        for force_tar, name in ((False, "rsync-target"), (True, "tar-target")):
            target = new_target(root, name)
            denied = install(source, target, force_tar=force_tar)
            assert denied.returncode != 0
            assert not (target / ".exocortex").exists()
        forbidden.unlink()

        checker = source / "scripts/check-public-release.py"
        race_canary = root / "mutable-source-installer-executed"
        malicious_install = (
            "#!/bin/bash\n"
            f": > {shlex.quote(str(race_canary))}\n"
            "exit 73\n"
        )
        text = checker.read_text(encoding="utf-8")
        needle = "from __future__ import annotations\n"
        probe = (
            needle
            + "\nimport os as _ambient_os\n"
            + "from pathlib import Path as _ambient_Path\n"
            + "if _ambient_os.environ.get('EXOCORTEX_AMBIENT_CANARY'):\n"
            + "    raise SystemExit('ambient environment reached candidate child')\n"
            + f"if _ambient_Path(__file__).resolve() == _ambient_Path({str(checker.resolve())!r}):\n"
            + "    raise SystemExit('installer executed checker from mutable source')\n"
            + "_race_update_snapshot = any('exocortex-update-env.' in item for item in __import__('sys').argv)\n"
            + "if not _race_update_snapshot and not _ambient_Path(__file__).with_name('SHA256SUMS.approved').is_file():\n"
            + "    raise SystemExit('approved manifest copy is not adjacent to checker copy')\n"
            + "if _race_update_snapshot:\n"
            + f"    _race_install = _ambient_Path({str((source / 'install.sh').resolve())!r})\n"
            + f"    _race_install.write_text({malicious_install!r}, encoding='utf-8')\n"
            + "    _race_install.chmod(0o755)\n"
            + f"    _ambient_Path({str((source / 'SHA256SUMS').resolve())!r}).write_text('concurrent source replacement\\n', encoding='utf-8')\n"
        )
        checker.write_text(text.replace(needle, probe, 1), encoding="utf-8")
        regenerate_integrity(source)
        ambient_target = new_target(root, "ambient-target")
        ambient = install(source, ambient_target, canary=True)
        assert ambient.returncode == 0, ambient.stderr
        assert "fictional-test-only" not in ambient.stdout + ambient.stderr

        clean_before = (clean_target / "AI_START_HERE.md").read_bytes()
        target_environments = {
            ".exocortex/.env.production",
            ".agents/skills/.env.local",
            ".cursor/skills/.envrc",
            ".claude/skills/.env.testing",
            ".github/skills/.env",
            ".windsurf/workflows/.env.staging",
        }
        environment_references = root / "environment-references"
        environment_references.mkdir()
        environment_modes: dict[str, int] = {}
        for index, relative in enumerate(sorted(target_environments)):
            target_environment = clean_target / relative
            target_environment.parent.mkdir(parents=True, exist_ok=True)
            target_environment.write_text(f"FICTIONAL_TARGET_ENV_CANARY_{index}\n", encoding="utf-8")
            target_environment.chmod(0o600)
            reference = environment_references / f"reference-{index}"
            shutil.copy2(target_environment, reference)
            environment_modes[relative] = stat.S_IMODE(target_environment.stat().st_mode)
        shadow_canary = root / "unlisted-import-shadow-executed"
        unlisted_shadow = source / "scripts/hashlib.py"
        unlisted_shadow.write_text(
            "from pathlib import Path\n"
            f"Path({str(shadow_canary)!r}).touch()\n"
            "raise RuntimeError('unlisted import shadow executed')\n",
            encoding="utf-8",
        )
        shadow_result = safe_update_dry_run(
            source, clean_target, root / "shadow-backups"
        )
        assert shadow_result.returncode != 0
        assert not shadow_canary.exists(), "unlisted snapshot module executed"
        unlisted_shadow.unlink()

        with (source / "AI_START_HERE.md").open("a", encoding="utf-8") as stream:
            stream.write("\n<!-- fictional safe-update candidate -->\n")
        regenerate_integrity(source)
        update = safe_update_dry_run(source, clean_target, root / "backups")
        assert update.returncode == 0, update.stderr
        assert "Dry run complete. Real target unchanged." in update.stdout
        assert (clean_target / "AI_START_HERE.md").read_bytes() == clean_before
        for index, relative in enumerate(sorted(target_environments)):
            target_environment = clean_target / relative
            compared = subprocess.run(
                ["cmp", "-s", str(environment_references / f"reference-{index}"), str(target_environment)],
                check=False,
            )
            assert compared.returncode == 0, f"protected environment bytes changed: {relative}"
            assert stat.S_IMODE(target_environment.stat().st_mode) == environment_modes[relative]
        assert not race_canary.exists(), "safe-update executed mutable source install.sh"
        assert not target_shadow_canary.exists(), "safe-update executed target Python shadow"
        assert (source / "SHA256SUMS").read_text(encoding="utf-8") == "concurrent source replacement\n"
        archives = list((root / "backups").glob("*.tar.gz.*"))
        assert len(archives) == 1
        with tarfile.open(archives[0], "r:gz") as archive:
            archive_names = {
                name[2:] if name.startswith("./") else name
                for name in archive.getnames()
            }
            assert not archive_names & target_environments
        assert "fictional-test-only" not in update.stdout + update.stderr

    print("installer_security_tests=pass")


if __name__ == "__main__":
    main()
