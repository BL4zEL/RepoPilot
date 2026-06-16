from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


# Folders that are useful to skip during a repository scan.
IGNORED_FOLDERS = {
    ".git",
    "venv",
    ".venv",
    "env",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    ".next",
    "coverage",
    "outputs",
}

# Files and file patterns that are usually noise for repo summaries.
IGNORED_FILE_NAMES = {
    ".DS_Store",
    "Thumbs.db",
}

IGNORED_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".log",
}

# Important files often tell us how a project is built or started.
IMPORTANT_FILE_NAMES = {
    "readme.md",
    "requirements.txt",
    "package.json",
    "pyproject.toml",
    "setup.py",
    "pipfile",
    "dockerfile",
    "docker-compose.yml",
    ".env.example",
    ".gitignore",
    "license",
    "app.py",
    "main.py",
    "index.html",
    "streamlit_app.py",
    "manage.py",
    "vite.config.js",
    "next.config.js",
    "platformio.ini",
}


def validate_repo_path(repo_path: str | Path) -> Path:
    """Return a resolved repo path after checking it exists and is a folder."""
    path = Path(repo_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"Repository path does not exist: {path}")

    if not path.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {path}")

    return path


def should_ignore_folder(folder_path: Path) -> bool:
    """Check whether a folder should be skipped during scanning."""
    return folder_path.name in IGNORED_FOLDERS


def should_ignore_file(file_path: Path) -> bool:
    """Check whether a file should be skipped during scanning."""
    if file_path.name in IGNORED_FILE_NAMES:
        return True

    return file_path.suffix.lower() in IGNORED_FILE_SUFFIXES


def is_important_file(file_path: Path) -> bool:
    """Detect project files that are useful for README generation later."""
    file_name = file_path.name.lower()

    if file_name in IMPORTANT_FILE_NAMES:
        return True

    return file_path.suffix.lower() == ".ino"


def to_relative_string(path: Path, root_path: Path) -> str:
    """Convert an absolute path into a clean repo-relative string."""
    return path.relative_to(root_path).as_posix()


def get_visible_items(directory_path: Path) -> list[Path]:
    """
    Return non-ignored directory items sorted with folders first, then files.

    Keeping this logic in one place helps the scanner and tree generator stay
    consistent with each other.
    """
    visible_items: list[Path] = []

    for item in directory_path.iterdir():
        if item.is_dir():
            if not should_ignore_folder(item):
                visible_items.append(item)
            continue

        if item.is_file() and not should_ignore_file(item):
            visible_items.append(item)

    return sorted(visible_items, key=lambda item: (not item.is_dir(), item.name.lower()))


def scan_directory(
    current_path: Path,
    root_path: Path,
    files: list[str],
    folders: list[str],
    important_files: list[str],
    extensions: Counter[str],
) -> None:
    """Recursively scan a directory and update the collector lists."""
    for item in get_visible_items(current_path):
        if item.is_dir():
            folders.append(to_relative_string(item, root_path))
            scan_directory(item, root_path, files, folders, important_files, extensions)
            continue

        if not item.is_file():
            continue

        relative_file = to_relative_string(item, root_path)
        files.append(relative_file)

        if is_important_file(item):
            important_files.append(relative_file)

        if item.suffix:
            extensions[item.suffix.lower()] += 1


def get_top_level_items(root_path: Path) -> tuple[list[str], list[str]]:
    """Collect top-level files and folders while respecting ignore rules."""
    top_level_files: list[str] = []
    top_level_folders: list[str] = []

    for item in get_visible_items(root_path):
        if item.is_dir():
            top_level_folders.append(item.name)
            continue

        if item.is_file():
            top_level_files.append(item.name)

    return top_level_files, top_level_folders


def build_tree_lines(
    current_path: Path,
    prefix: str,
    current_depth: int,
    max_depth: int,
    max_items_per_folder: int,
    lines: list[str],
) -> None:
    """Recursively build a markdown-friendly tree structure."""
    items = get_visible_items(current_path)
    hidden_items = max(0, len(items) - max_items_per_folder)
    visible_items = items[:max_items_per_folder]

    for index, item in enumerate(visible_items):
        is_last_visible_item = index == len(visible_items) - 1 and hidden_items == 0
        branch = "└── " if is_last_visible_item else "├── "
        item_name = f"{item.name}/" if item.is_dir() else item.name
        lines.append(f"{prefix}{branch}{item_name}")

        if not item.is_dir():
            continue

        child_prefix = f"{prefix}{'    ' if is_last_visible_item else '│   '}"

        # Once we hit the depth limit, we hint that deeper content exists
        # without dumping a huge tree into the output.
        if current_depth >= max_depth:
            if get_visible_items(item):
                lines.append(f"{child_prefix}└── ...")
            continue

        build_tree_lines(
            item,
            child_prefix,
            current_depth + 1,
            max_depth,
            max_items_per_folder,
            lines,
        )

    if hidden_items > 0:
        lines.append(f"{prefix}└── ... more items hidden")


def generate_project_tree(
    repo_path: str | Path,
    max_depth: int = 4,
    max_items_per_folder: int = 30,
) -> str:
    """Generate a readable project tree for the given repository path."""
    if max_depth < 1:
        raise ValueError("max_depth must be at least 1.")

    if max_items_per_folder < 1:
        raise ValueError("max_items_per_folder must be at least 1.")

    root_path = validate_repo_path(repo_path)
    lines = [f"{root_path.name}/"]

    build_tree_lines(
        current_path=root_path,
        prefix="",
        current_depth=1,
        max_depth=max_depth,
        max_items_per_folder=max_items_per_folder,
        lines=lines,
    )

    return "\n".join(lines)


def scan_repository(
    repo_path: str | Path,
    max_depth: int = 4,
    max_items_per_folder: int = 30,
    include_tech_stack: bool = True,
    include_run_instructions: bool = True,
) -> dict:
    """
    Scan a local repository and return a structured summary dictionary.

    This function is intentionally reusable so other project files can import it.
    """
    root_path = validate_repo_path(repo_path)

    files: list[str] = []
    folders: list[str] = []
    important_files: list[str] = []
    extensions: Counter[str] = Counter()

    scan_directory(root_path, root_path, files, folders, important_files, extensions)
    top_level_files, top_level_folders = get_top_level_items(root_path)
    project_tree = generate_project_tree(
        root_path,
        max_depth=max_depth,
        max_items_per_folder=max_items_per_folder,
    )

    result = {
        "repo_path": str(root_path),
        "repo_name": root_path.name,
        "files": files,
        "folders": folders,
        "important_files": important_files,
        "top_level_files": top_level_files,
        "top_level_folders": top_level_folders,
        "extensions": dict(sorted(extensions.items())),
        "total_files": len(files),
        "total_folders": len(folders),
        "project_tree": project_tree,
    }

    if include_tech_stack:
        from tech_detector import detect_tech_stack

        result["tech_stack"] = detect_tech_stack(root_path, scan_result=result)

    if include_run_instructions:
        from run_detector import detect_run_instructions

        result["run_instructions"] = detect_run_instructions(
            root_path,
            scan_result=result,
            tech_stack=result.get("tech_stack"),
        )

    return result


def main() -> int:
    """Simple CLI entry point for testing the scanner manually."""
    if len(sys.argv) != 2:
        print("Usage: python repo_scanner.py path/to/repo", file=sys.stderr)
        return 1

    try:
        result = scan_repository(sys.argv[1])
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    try:
        print(json.dumps(result, indent=4, ensure_ascii=False))
    except UnicodeEncodeError:
        print(json.dumps(result, indent=4))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
