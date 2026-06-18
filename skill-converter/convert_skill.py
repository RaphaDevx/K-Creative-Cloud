#!/usr/bin/env python3
"""
Skill Converter: Claude Code Skill (.md) → Qwen/Ollama Modelfile + OpenWebUI JSON + plain .txt

Usage:
    python3 convert_skill.py <skill.md> [--model qwen3:8b] [--output-dir ./output]
    python3 convert_skill.py --all ~/.claude/commands/ [--model qwen3:8b]

Output formats:
    - Ollama Modelfile  (FROM <model> + SYSTEM block)
    - OpenWebUI prompt  (JSON, importable via /workspace/prompts)
    - Plain system prompt .txt (universal)
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

DEFAULT_MODEL = "qwen3:8b"
SKILL_REGISTRY_PATH = Path(__file__).parent / "skill_registry.json"


def parse_skill_md(filepath: Path) -> dict:
    """Parse a Claude Code skill .md file.
    Returns dict with: name, description, frontmatter, body, raw_content
    """
    raw = filepath.read_text(encoding="utf-8")

    # Extract YAML frontmatter (--- ... ---)
    frontmatter = {}
    body = raw
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1)
        body = raw[fm_match.end():]
        for line in fm_text.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                frontmatter[key.strip()] = val.strip()

    # Derive skill name from frontmatter or filename
    name = frontmatter.get("name") or filepath.stem

    # Description from frontmatter or first H1/paragraph
    description = frontmatter.get("description", "")
    if not description:
        h1 = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        if h1:
            description = h1.group(1).strip()

    return {
        "name": name,
        "description": description,
        "frontmatter": frontmatter,
        "body": body.strip(),
        "raw_content": raw,
        "filepath": str(filepath),
    }


def to_ollama_modelfile(skill: dict, model: str = DEFAULT_MODEL) -> str:
    """Convert skill to Ollama Modelfile format."""
    system_prompt = skill["body"]

    # Clean up markdown for use as system prompt
    # Remove HTML comments, excessive blank lines
    system_prompt = re.sub(r"<!--.*?-->", "", system_prompt, flags=re.DOTALL)
    system_prompt = re.sub(r"\n{3,}", "\n\n", system_prompt).strip()

    lines = [
        f"FROM {model}",
        "",
        "# Converted from Claude Code skill: " + skill["name"],
        f"# Source: {skill['filepath']}",
        f"# Converted: {datetime.now().strftime('%Y-%m-%d')}",
        "",
        'SYSTEM """',
        system_prompt,
        '"""',
        "",
        "# Recommended parameters for instruction following",
        "PARAMETER temperature 0.7",
        "PARAMETER top_p 0.9",
        "PARAMETER num_ctx 8192",
    ]
    return "\n".join(lines)


def to_openwebui_prompt(skill: dict) -> dict:
    """Convert skill to OpenWebUI importable JSON format."""
    # OpenWebUI Prompt format (compatible with /workspace/prompts import)
    system_prompt = skill["body"]
    system_prompt = re.sub(r"<!--.*?-->", "", system_prompt, flags=re.DOTALL)
    system_prompt = re.sub(r"\n{3,}", "\n\n", system_prompt).strip()

    return {
        "id": skill["name"].replace(" ", "-").lower(),
        "title": skill.get("description") or skill["name"],
        "command": skill["name"],
        "content": system_prompt,
        "timestamp": int(datetime.now().timestamp()),
        "meta": {
            "source": "claude-code-skill",
            "original_path": skill["filepath"],
            "converted": datetime.now().isoformat(),
            "description": skill.get("description", ""),
        },
    }


def to_plain_txt(skill: dict) -> str:
    """Convert skill to plain system prompt .txt (universal, works with any LLM API)."""
    system_prompt = skill["body"]
    system_prompt = re.sub(r"<!--.*?-->", "", system_prompt, flags=re.DOTALL)
    system_prompt = re.sub(r"\n{3,}", "\n\n", system_prompt).strip()
    return system_prompt


def update_registry(skill: dict, output_paths: dict, registry_path: Path = SKILL_REGISTRY_PATH):
    """Update skill_registry.json with the converted skill."""
    registry = {}
    if registry_path.exists():
        with open(registry_path) as f:
            registry = json.load(f)

    registry[skill["name"]] = {
        "name": skill["name"],
        "description": skill.get("description", ""),
        "claude_path": skill["filepath"],
        "ollama_modelfile": output_paths.get("modelfile", ""),
        "openwebui_prompt": output_paths.get("openwebui", ""),
        "plain_txt": output_paths.get("txt", ""),
        "best_qwen_approach": _recommend_qwen_approach(skill),
        "last_converted": datetime.now().isoformat(),
    }

    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    return registry


def _recommend_qwen_approach(skill: dict) -> str:
    """Heuristic: recommend best approach for Qwen based on skill content."""
    body = skill["body"].lower()
    name = skill["name"].lower()

    # Skills that call MCPs / tools → modelfile won't help much, use system_prompt
    if "mcp" in body or "tool_call" in body or "function" in body:
        return "system_prompt"

    # Skills with persistent persona → modelfile is best
    if any(w in body for w in ["du bist", "you are", "dein stil", "your role"]):
        return "modelfile"

    # Multi-step pipeline skills → openwebui with prompt template
    if any(w in body for w in ["schritt", "step", "pipeline", "phase"]):
        return "openwebui_prompt"

    return "system_prompt"


def convert_skill(skill_path: Path, output_dir: Path, model: str = DEFAULT_MODEL) -> dict:
    """Convert a single skill file to all formats. Returns output paths."""
    skill = parse_skill_md(skill_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    modelfiles_dir = output_dir.parent / "modelfiles"
    prompts_dir = output_dir.parent / "prompts"
    txt_dir = output_dir.parent / "system_prompts"
    for d in [modelfiles_dir, prompts_dir, txt_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Write Ollama Modelfile
    mf_path = modelfiles_dir / f"{skill['name']}.Modelfile"
    mf_path.write_text(to_ollama_modelfile(skill, model), encoding="utf-8")

    # Write OpenWebUI JSON
    ow_path = prompts_dir / f"{skill['name']}.json"
    ow_path.write_text(json.dumps(to_openwebui_prompt(skill), indent=2, ensure_ascii=False), encoding="utf-8")

    # Write plain TXT
    txt_path = txt_dir / f"{skill['name']}.txt"
    txt_path.write_text(to_plain_txt(skill), encoding="utf-8")

    output_paths = {
        "modelfile": str(mf_path),
        "openwebui": str(ow_path),
        "txt": str(txt_path),
    }

    update_registry(skill, output_paths)

    print(f"[OK] {skill['name']}")
    print(f"     Modelfile  → {mf_path}")
    print(f"     OpenWebUI  → {ow_path}")
    print(f"     Plain TXT  → {txt_path}")
    print(f"     Qwen best  → {_recommend_qwen_approach(skill)}")

    return output_paths


def main():
    parser = argparse.ArgumentParser(description="Convert Claude Code Skills to Qwen/Ollama formats")
    parser.add_argument("skill", nargs="?", help="Path to skill .md file")
    parser.add_argument("--all", metavar="DIR", help="Convert all .md files in directory")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model (default: {DEFAULT_MODEL})")
    parser.add_argument("--output-dir", default=str(Path(__file__).parent), help="Output base directory")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    if args.all:
        skills_dir = Path(args.all).expanduser()
        md_files = list(skills_dir.rglob("*.md"))
        if not md_files:
            print(f"No .md files found in {skills_dir}", file=sys.stderr)
            sys.exit(1)
        print(f"Converting {len(md_files)} skills from {skills_dir} ...\n")
        for md_file in sorted(md_files):
            try:
                convert_skill(md_file, output_dir / "converted", args.model)
            except Exception as e:
                print(f"[ERROR] {md_file.name}: {e}", file=sys.stderr)
    elif args.skill:
        skill_path = Path(args.skill).expanduser()
        if not skill_path.exists():
            print(f"File not found: {skill_path}", file=sys.stderr)
            sys.exit(1)
        convert_skill(skill_path, output_dir / "converted", args.model)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
