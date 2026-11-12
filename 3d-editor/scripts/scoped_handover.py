"""Scoped staging for the mandatory K-Dev handover; never commits/pushes itself.

Prepare an alternate index, preflight a two-tree merge preserving existing
staging, install it only for the API call, and restore foreign staging afterwards.
Private recovery indexes and the API receipt are retained outside the repository.
Requires a coordinated exclusive Git window: the helper guard serializes this
utility, but external Git writers do not honor it. Signer-side immutable-tree
handover would be needed for a general concurrent-writer guarantee.
"""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path, PurePosixPath
import re
import socket
import stat
import subprocess
import tempfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def allowed(path, prefixes):
    return any(path == prefix or path.startswith(prefix + "/") for prefix in prefixes)


def git(repo, *args, index=None, check=True):
    env = dict(os.environ)
    env.pop("GIT_INDEX_FILE", None)
    if index is not None:
        env["GIT_INDEX_FILE"] = str(index)
    result = subprocess.run(["git", *args], cwd=repo, env=env, capture_output=True)
    if check and result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace").strip())
    return result.stdout


def names(repo, tree, index=None):
    return set(filter(None, git(repo, "diff", "--cached", "--no-renames", "--name-only", "-z", tree, index=index).split(b"\0")))


def entries(repo, index=None):
    return git(repo, "ls-files", "--stage", "-z", index=index)


def install_index(path, data, mode, verify):
    lock = path.with_name(path.name + ".lock")
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    owned_inode = os.fstat(fd).st_ino
    replaced = False
    try:
        verify()
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb", closefd=False) as file:
            file.write(data)
            file.flush()
            os.fsync(fd)
        os.replace(lock, path)
        replaced = True
    finally:
        os.close(fd)
        if not replaced and lock.exists() and lock.stat().st_ino == owned_inode:
            lock.unlink()


def terminal_response(status, body):
    """Proxy timeouts/503 and an already-running signer/409 remain unknown."""
    if not isinstance(body, dict):
        return False
    if status in (200, 202):
        return (body.get("handedOver") is True and body.get("signed") is True
                and isinstance(body.get("project"), str)
                and isinstance(body.get("commit"), str)
                and re.fullmatch(r"[0-9a-f]{40}", body["commit"]) is not None
                and isinstance(body.get("pushed"), list)
                and all(isinstance(remote, str) for remote in body["pushed"]))
    return (status in (400, 403, 404, 422, 500, 502)
            and body.get("stage") == "commit" and isinstance(body.get("error"), str))


class UnixConnection(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__("kdev", timeout=360)
        self.socket_path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.socket_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--message", required=True)
    parser.add_argument("--project", default="kcreative")
    parser.add_argument("--socket", default=os.environ.get("KDEV_CLI_SOCKET", "/srv/k-dev/state/cli/api.sock"))
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--exclusive-git-window", action="store_true")
    args = parser.parse_args()
    repo = args.repo.resolve()
    prefixes = json.loads(args.manifest.read_text())
    if not isinstance(prefixes, list) or not prefixes or any(
        not isinstance(p, str) or not p or PurePosixPath(p).is_absolute()
        or any(part in ("..", ".git") for part in PurePosixPath(p).parts)
        or str(PurePosixPath(p)) != p or p == "." for p in prefixes
    ):
        raise RuntimeError("Manifest must contain explicit repository-relative paths")
    if git(repo, "ls-files", "-u"):
        raise RuntimeError("Resolve unmerged index entries before handover")
    index = Path(git(repo, "rev-parse", "--git-path", "index").decode().strip())
    if not index.is_absolute():
        index = repo / index
    original = index.read_bytes()
    mode = stat.S_IMODE(index.stat().st_mode)
    head = git(repo, "rev-parse", "HEAD").decode().strip()
    foreign = names(repo, head)
    if any(allowed(p.decode(), prefixes) for p in foreign):
        raise RuntimeError("Selected files already have staged changes; preserve that staging explicitly first")
    recovery = Path(tempfile.mkdtemp(prefix="kcreative-handover-"))
    original_path = recovery / "original.index"
    original_path.write_bytes(original)
    original_path.chmod(0o600)
    target = recovery / "target.index"
    git(repo, "read-tree", head, index=target)
    git(repo, "add", "--", *prefixes, index=target)
    staged = names(repo, head, index=target)
    if not staged:
        print(json.dumps({"ok": True, "unchanged": True, "recovery": str(recovery)}))
        return
    if any(not allowed(p.decode(), prefixes) for p in staged):
        raise RuntimeError("Alternate index contains a file outside the declared scope")
    tree = git(repo, "write-tree", index=target).decode().strip()
    restored = recovery / "restored.index"
    restored.write_bytes(original)
    git(repo, "read-tree", "-i", "-m", head, tree, index=restored)
    if names(repo, tree, index=restored) != foreign:
        raise RuntimeError("Preflight did not preserve exactly the existing staged paths")
    original_entries = entries(repo)
    preserved_entries = entries(repo, index=restored)
    def foreign_entries(data):
        return sorted(line for line in data.split(b"\0") if line and line.split(b"\t", 1)[1] in foreign)
    if foreign_entries(original_entries) != foreign_entries(preserved_entries):
        raise RuntimeError("Preflight changed staged blob IDs/modes")
    expected_entries = entries(repo, index=target)
    plan = {"old_head": head, "tree": tree, "files": sorted(p.decode() for p in staged),
            "preserved_staged_paths": len(foreign), "recovery": str(recovery)}
    (recovery / "plan.json").write_text(json.dumps(plan, indent=2))
    if not args.execute:
        print(json.dumps({"ok": True, "dry_run": True, **plan}))
        return
    if not args.exclusive_git_window:
        raise RuntimeError("Stop other project Git writers and pass --exclusive-git-window before executing")

    def before_install():
        if digest(index.read_bytes()) != digest(original) or git(repo, "rev-parse", "HEAD").decode().strip() != head:
            raise RuntimeError("Repository changed since preflight; nothing installed")

    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,39}", args.project) or not args.message.strip():
        raise RuntimeError("A valid project and nonempty message are required")
    # Establish that the selected K-Dev project actually signs this repository,
    # rather than trusting an arbitrary valid project ID from the caller.
    probe = UnixConnection(args.socket)
    try:
        probe.request("GET", "/api/project-check/" + args.project)
        response = probe.getresponse()
        project_check = json.loads(response.read())
        mapped = next((r.get("detail") for r in project_check.get("results", [])
                       if r.get("rule") == "pfad" and r.get("status") == "ok"), None)
        if response.status != 200 or not mapped or Path(mapped).resolve() != repo:
            raise RuntimeError("K-Dev project does not map to this repository")
    finally:
        probe.close()
    if not all(git(repo, "config", "--local", "--get", key, check=False).strip()
               for key in ("user.name", "user.email")):
        raise RuntimeError("Configure explicit local author name/email; signer has its own global defaults")
    guard = index.parent / "kdev-handover.guard"
    guard_fd = os.open(guard, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.write(guard_fd, json.dumps({"pid": os.getpid(), "recovery": str(recovery)}).encode())
    os.close(guard_fd)
    retain_guard = False
    installed = False
    request_possible = False
    status = None
    body = {}
    try:
        install_index(index, target.read_bytes(), mode, before_install)
        installed = True
        connection = UnixConnection(args.socket)
        try:
            payload = json.dumps({"project": args.project, "message": args.message}).encode()
            request_possible = True
            connection.request("POST", "/api/handover", body=payload,
                               headers={"Content-Type": "application/json"})
            response = connection.getresponse()
            status = response.status
            raw = response.read()
            body = json.loads(raw)
        except (ConnectionRefusedError, FileNotFoundError):
            request_possible = False
            raise
        finally:
            connection.close()
    finally:
        if installed:
            current_head = git(repo, "rev-parse", "HEAD").decode().strip()
            current_tree = git(repo, "rev-parse", "HEAD^{tree}").decode().strip()
            same_head = current_head == head
            if request_possible and not terminal_response(status, body):
                retain_guard = True
                raise RuntimeError(f"API outcome unknown; index left isolated. Recovery: {recovery}")
            if entries(repo) != expected_entries or (not same_head and current_tree != tree):
                retain_guard = True
                raise RuntimeError(f"Concurrent repository/index change; no blind restoration. Recovery: {recovery}")
            if not same_head and git(repo, "rev-parse", "HEAD^").decode().strip() != head:
                retain_guard = True
                raise RuntimeError(f"Unexpected commit ancestry. Recovery: {recovery}")
            def before_restore():
                if git(repo, "rev-parse", "HEAD").decode().strip() != current_head or entries(repo) != expected_entries:
                    raise RuntimeError(f"Repository changed before restoration. Recovery: {recovery}")
            install_index(index, original if same_head else restored.read_bytes(), mode, before_restore)
            if names(repo, current_head) != foreign or foreign_entries(entries(repo)) != foreign_entries(original_entries):
                retain_guard = True
                raise RuntimeError(f"Restored staging failed independent verification. Recovery: {recovery}")
            success = (status in (200, 202) and not same_head and body.get("project") == args.project
                       and body.get("commit") == current_head and body.get("files") == len(staged))
            receipt = {"ok": success, "status": status, "response": body,
                       "commit": None if same_head else current_head,
                       "foreign_staging_restored": True, **plan}
            (recovery / "receipt.json").write_text(json.dumps(receipt, indent=2))
            print(json.dumps(receipt))
        if not retain_guard:
            guard.unlink()
    if not receipt["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, http.client.HTTPException) as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        raise SystemExit(1)
