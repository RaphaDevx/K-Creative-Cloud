#!/usr/bin/env python3
"""
sync_skills.py — Watches Claude Code skill directories and auto-converts on change.

Monitors:
    - ~/.claude/commands/          (user skills)
    - /usr/local/share/claude-skills/  (shared skills)

On change: converts to all Qwen formats via convert_skill.py.
Optional: git commit if output dir is a git repo.

Usage:
    python3 sync_skills.py [--watch] [--once] [--git-commit]

Dependencies:
    pip install watchdog   (for --watch mode)
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONVERT_SCRIPT = SCRIPT_DIR / "convert_skill.py"
REGISTRY_PATH = SCRIPT_DIR / "skill_registry.json"

WATCH_DIRS = [
    Path.home() / ".claude" / "commands",
    Path("/usr/local/share/claude-skills"),
    # Also watch the shared skills symlink if present
    Path("/home/claude/.claude/commands"),
]

OUTPUT_DIR = SCRIPT_DIR


def run_conversion(skill_path: Path, model: str = "qwen3:8b") -> bool:
    """Run convert_skill.py for a single skill file."""
    cmd = [sys.executable, str(CONVERT_SCRIPT), str(skill_path), "--model", model, "--output-dir", str(OUTPUT_DIR)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"[sync] Converted: {skill_path.name}")
        print(result.stdout)
        return True
    else:
        print(f"[sync] ERROR converting {skill_path.name}: {result.stderr}", file=sys.stderr)
        return False


def sync_all(model: str = "qwen3:8b") -> int:
    """One-shot: convert all skills in all watch dirs. Returns count converted."""
    count = 0
    seen = set()
    for watch_dir in WATCH_DIRS:
        if not watch_dir.exists():
            continue
        for md_file in watch_dir.rglob("*.md"):
            # Skip reference/benchmark files
            if md_file.stem.startswith("_") or "benchmark" in md_file.stem:
                continue
            key = md_file.stem
            if key in seen:
                continue
            seen.add(key)
            if run_conversion(md_file, model):
                count += 1
    return count


def git_commit_if_repo(message: str = "chore: auto-sync skill conversions"):
    """If OUTPUT_DIR is inside a git repo, stage and commit changes."""
    try:
        result = subprocess.run(
            ["git", "-C", str(OUTPUT_DIR), "status", "--porcelain"],
            capture_output=True, text=True
        )
        if result.returncode != 0 or not result.stdout.strip():
            return False  # not a git repo or nothing changed

        # Stage skill-converter directory
        subprocess.run(["git", "-C", str(OUTPUT_DIR.parent), "add", "skill-converter/"], check=True)
        subprocess.run(
            ["git", "-C", str(OUTPUT_DIR.parent), "commit", "-m", message,
             "--author", "raphael <raphael.m.kaufmann@gmail.com>"],
            check=True
        )
        print(f"[git] Committed: {message}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[git] Commit failed: {e}", file=sys.stderr)
        return False


def watch_mode(model: str = "qwen3:8b", git_commit: bool = False):
    """Watch skill directories for changes using watchdog."""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print("watchdog not installed. Install with: pip install watchdog", file=sys.stderr)
        print("Falling back to polling mode (check every 30s)...", file=sys.stderr)
        polling_mode(model, git_commit)
        return

    class SkillHandler(FileSystemEventHandler):
        def __init__(self):
            self.last_processed = {}

        def on_modified(self, event):
            self._handle(event)

        def on_created(self, event):
            self._handle(event)

        def _handle(self, event):
            if event.is_directory:
                return
            path = Path(event.src_path)
            if path.suffix != ".md":
                return
            # Debounce: skip if processed within last 2s
            now = time.time()
            if now - self.last_processed.get(str(path), 0) < 2:
                return
            self.last_processed[str(path)] = now

            print(f"\n[watch] Change detected: {path.name}")
            if run_conversion(path, model) and git_commit:
                git_commit_if_repo(f"chore: auto-convert skill {path.stem}")

    observer = Observer()
    handler = SkillHandler()
    watched = []
    for watch_dir in WATCH_DIRS:
        if watch_dir.exists():
            observer.schedule(handler, str(watch_dir), recursive=True)
            watched.append(watch_dir)

    if not watched:
        print("No skill directories found to watch.", file=sys.stderr)
        sys.exit(1)

    print(f"[watch] Watching {len(watched)} directories:")
    for d in watched:
        print(f"        {d}")
    print("[watch] Press Ctrl+C to stop.\n")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def polling_mode(model: str = "qwen3:8b", git_commit: bool = False, interval: int = 30):
    """Fallback polling mode: check for changes every <interval> seconds."""
    print(f"[poll] Polling every {interval}s. Press Ctrl+C to stop.")
    mtimes = {}

    while True:
        changed = []
        for watch_dir in WATCH_DIRS:
            if not watch_dir.exists():
                continue
            for md_file in watch_dir.rglob("*.md"):
                mtime = md_file.stat().st_mtime
                if mtimes.get(str(md_file)) != mtime:
                    mtimes[str(md_file)] = mtime
                    changed.append(md_file)

        for path in changed:
            print(f"\n[poll] Change detected: {path.name}")
            run_conversion(path, model)

        if changed and git_commit:
            git_commit_if_repo()

        time.sleep(interval)


def print_registry():
    """Print the current skill registry."""
    if not REGISTRY_PATH.exists():
        print("No registry found. Run --once first.")
        return
    registry = json.loads(REGISTRY_PATH.read_text())
    print(f"\nSkill Registry ({len(registry)} skills):\n")
    for name, info in sorted(registry.items()):
        print(f"  {name}")
        print(f"    Claude: {info.get('claude_path', '-')}")
        print(f"    Qwen:   {info.get('best_qwen_approach', '-')}")
        print(f"    Model:  {info.get('ollama_modelfile', '-')}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Sync Claude Code Skills → Qwen/Ollama formats")
    parser.add_argument("--watch", action="store_true", help="Watch for file changes (requires watchdog)")
    parser.add_argument("--once", action="store_true", help="One-shot: convert all skills now")
    parser.add_argument("--git-commit", action="store_true", help="Auto-commit after conversion")
    parser.add_argument("--model", default="qwen3:8b", help="Target Ollama model")
    parser.add_argument("--list", action="store_true", help="Print skill registry")
    args = parser.parse_args()

    if args.list:
        print_registry()
        return

    if args.once:
        print("Converting all skills...\n")
        count = sync_all(args.model)
        print(f"\nDone. Converted {count} skills.")
        if args.git_commit and count > 0:
            git_commit_if_repo(f"chore: bulk convert {count} skills to Qwen/Ollama format")
        return

    if args.watch:
        watch_mode(args.model, args.git_commit)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
