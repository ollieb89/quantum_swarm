#!/usr/bin/env python3
"""Generate Obsidian transclusion index pages for tracked directories.

Creates notes in the Obsidian vault that use ![[file]] transclusions to embed
content from .gemini-kit and .planning directories. This surfaces plugin context
and planning state inside Obsidian without duplicating any content.

The script is idempotent — safe to run from cron, CI, or manually.

Usage:
    python scripts/generate_transclusion_indexes.py [--vault-root PATH] [--project SLUG]
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
from typing import List


def discover_markdown_files(directory: Path) -> List[Path]:
    """Find all .md files in a directory, sorted by name."""
    if not directory.exists():
        return []
    return sorted(directory.glob("*.md"))


def vault_transclusion_path(file_path: Path, source_dir: Path, vault_alias: str) -> str:
    """Build an Obsidian transclusion path using the vault symlink alias.

    Obsidian ignores dotfiles, so .gemini-kit and .planning are symlinked
    into the vault as 'gemini-kit' and 'planning'. Transclusions reference
    files through these non-hidden symlink names.
    """
    return f"{vault_alias}/{file_path.relative_to(source_dir)}"


def generate_plugin_context_page(
    vault_root: Path, project_slug: str, gemini_kit_dir: Path
) -> Path:
    """Generate Plugin-Context.md with transclusions from .gemini-kit."""
    project_dir = vault_root / "Projects" / project_slug
    project_dir.mkdir(parents=True, exist_ok=True)
    target = project_dir / "Plugin-Context.md"

    files = discover_markdown_files(gemini_kit_dir)
    today = dt.date.today().isoformat()

    lines = [
        "---",
        f"project: {project_slug}",
        f"updated: {today}",
        "generated: true",
        "tags:",
        f"  - project/{project_slug}",
        "  - context/plugins",
        "---",
        "",
        "# Plugin Context",
        "",
        "> Auto-generated from `.gemini-kit/`. Do not edit manually.",
        "",
    ]

    if files:
        for f in files:
            name = f.stem.replace("-", " ").replace("_", " ").title()
            rel = vault_transclusion_path(f, gemini_kit_dir, "gemini-kit")
            lines.extend([
                f"## {name}",
                "",
                f"![[{rel}]]",
                "",
            ])
    else:
        lines.append("No plugin context files found in `.gemini-kit/`.")

    lines.extend([
        "## Links",
        "",
        f"- [[Projects/{project_slug}/Overview]]",
        f"- [[Projects/{project_slug}/Plans]]",
        "",
    ])

    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def generate_plans_page(
    vault_root: Path, project_slug: str, planning_dir: Path
) -> Path:
    """Generate Plans.md with transclusions from .planning."""
    project_dir = vault_root / "Projects" / project_slug
    project_dir.mkdir(parents=True, exist_ok=True)
    target = project_dir / "Plans.md"

    today = dt.date.today().isoformat()

    # Priority files first, then other top-level, then PHASES/
    priority = ["STATE.md", "ROADMAP.md", "DECISIONS.md"]
    priority_files = [planning_dir / p for p in priority if (planning_dir / p).exists()]
    other_files = [
        f for f in discover_markdown_files(planning_dir)
        if f.name not in priority
    ]
    phase_files = discover_markdown_files(planning_dir / "PHASES")

    lines = [
        "---",
        f"project: {project_slug}",
        f"updated: {today}",
        "generated: true",
        "tags:",
        f"  - project/{project_slug}",
        "  - planning",
        "---",
        "",
        "# Plans & State",
        "",
        "> Auto-generated from `.planning/`. Do not edit manually.",
        "",
    ]

    for f in priority_files:
        name = f.stem.replace("-", " ").replace("_", " ").title()
        rel = vault_transclusion_path(f, planning_dir, "planning")
        lines.extend([
            f"## {name}",
            "",
            f"![[{rel}]]",
            "",
        ])

    if other_files:
        lines.extend(["## Other Planning Documents", ""])
        for f in other_files:
            name = f.stem.replace("-", " ").replace("_", " ").title()
            rel = vault_transclusion_path(f, planning_dir, "planning")
            lines.extend([
                f"### {name}",
                "",
                f"![[{rel}]]",
                "",
            ])

    if phase_files:
        lines.extend(["## Phase Plans", ""])
        for f in phase_files:
            name = f.stem.replace("-", " ").replace("_", " ").title()
            rel = vault_transclusion_path(f, planning_dir, "planning")
            lines.extend([
                f"### {name}",
                "",
                f"![[{rel}]]",
                "",
            ])

    if not priority_files and not other_files and not phase_files:
        lines.append("No planning documents found in `.planning/`.")

    lines.extend([
        "## Links",
        "",
        f"- [[Projects/{project_slug}/Overview]]",
        f"- [[Projects/{project_slug}/Plugin-Context]]",
        "",
    ])

    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def ensure_vault_symlinks(vault_root: Path, repo_root: Path) -> None:
    """Ensure symlinks exist in the vault for dotfile directories.

    Obsidian ignores hidden directories, so we symlink .gemini-kit and
    .planning into the vault with non-hidden names.
    """
    links = {
        "gemini-kit": repo_root / ".gemini-kit",
        "planning": repo_root / ".planning",
    }
    for name, target in links.items():
        link_path = vault_root / name
        if target.exists() and not link_path.exists():
            link_path.symlink_to(target.resolve())
            print(f"Created symlink: {link_path} -> {target}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Obsidian transclusion indexes.")
    parser.add_argument("--vault-root", default="quantum-swarm", help="Vault root path")
    parser.add_argument("--project", default="quantum-swarm", help="Project slug")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    vault_root = Path(args.vault_root)
    gemini_kit = repo_root / ".gemini-kit"
    planning = repo_root / ".planning"

    ensure_vault_symlinks(vault_root, repo_root)

    updated = []

    ctx_page = generate_plugin_context_page(vault_root, args.project, gemini_kit)
    updated.append(str(ctx_page))

    plans_page = generate_plans_page(vault_root, args.project, planning)
    updated.append(str(plans_page))

    for path in updated:
        print(f"Updated: {path}")


if __name__ == "__main__":
    main()
