"""Install the canonical skill into a selected project's agent directory."""
import argparse
from pathlib import Path
import shutil
import sys


def install(project, agent):
    source = Path(__file__).resolve().parent / ".agents" / "skills" / "video-edit"
    project = Path(project).resolve()
    if not project.is_dir():
        raise ValueError("Select an existing project directory")
    folder = ".agents" if agent == "codex" else ".claude"
    destination = project / folder / "skills" / "video-edit"
    if destination.resolve() == source:
        return str(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError("Skill exists; review the existing version before replacing it")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    return str(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=("codex", "claude"), required=True)
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    try:
        print(install(args.project, args.agent))
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
