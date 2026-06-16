from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from repo_scanner import scan_repository, validate_repo_path
from tech_detector import detect_tech_stack


MAX_READ_SIZE = 50 * 1024

SAFE_TEXT_SUFFIXES = {
    ".py",
    ".toml",
    ".json",
    ".txt",
    ".ini",
    ".yml",
    ".yaml",
    ".env",
}

SAFE_TEXT_FILE_NAMES = {
    "requirements.txt",
    "pyproject.toml",
    "pipfile",
    "package.json",
    ".env.example",
    "platformio.ini",
    "app.py",
    "main.py",
    "manage.py",
    "streamlit_app.py",
}

DATABASE_NOTE_VALUES = {
    "MongoDB",
    "Firebase",
    "Supabase",
    "PostgreSQL",
    "MySQL",
}


def make_empty_run_info() -> dict:
    """Create the default run instruction structure."""
    return {
        "setup_steps": [],
        "run_commands": [],
        "notes": [],
        "detected_entry_points": [],
    }


def add_unique(items: list[str], value: str) -> None:
    """Append a value once while preserving insertion order."""
    if value not in items:
        items.append(value)


def safe_read_text(file_path: Path, max_size: int = MAX_READ_SIZE) -> str:
    """Read a small chunk of text without crashing on encoding issues."""
    try:
        with file_path.open("r", encoding="utf-8", errors="ignore") as file_handle:
            return file_handle.read(max_size)
    except (OSError, UnicodeError):
        return ""


def is_safe_text_file(file_path: Path) -> bool:
    """Check whether a file is reasonable to inspect as text."""
    if file_path.name.lower() in SAFE_TEXT_FILE_NAMES:
        return True

    return file_path.suffix.lower() in SAFE_TEXT_SUFFIXES


def get_file_map(repo_path: Path, scan_result: dict) -> dict[str, Path]:
    """Map repo-relative file paths to absolute file paths."""
    return {
        relative_path: repo_path / Path(relative_path)
        for relative_path in scan_result.get("files", [])
    }


def find_paths_by_name(file_map: dict[str, Path], file_name: str) -> list[str]:
    """Find repo-relative paths that match a specific filename."""
    matches = [
        relative_path
        for relative_path, absolute_path in file_map.items()
        if absolute_path.name.lower() == file_name.lower()
    ]
    return sorted(matches, key=lambda path: (path.count("/"), path.lower()))


def get_preferred_path(file_map: dict[str, Path], file_name: str) -> str | None:
    """Return the best matching path for a filename, preferring shallower files."""
    matches = find_paths_by_name(file_map, file_name)
    return matches[0] if matches else None


def read_package_json_scripts(package_json_path: Path) -> dict[str, str]:
    """Read package.json scripts safely and return a simple string map."""
    text = safe_read_text(package_json_path)
    if not text:
        return {}

    try:
        package_data = json.loads(text)
    except json.JSONDecodeError:
        return {}

    scripts = package_data.get("scripts", {})
    if not isinstance(scripts, dict):
        return {}

    cleaned_scripts: dict[str, str] = {}
    for script_name, script_value in scripts.items():
        if isinstance(script_name, str) and isinstance(script_value, str):
            cleaned_scripts[script_name] = script_value

    return cleaned_scripts


def module_path_from_relative_path(relative_path: str) -> str:
    """Convert a repo-relative Python file path into a dotted module path."""
    path = Path(relative_path)
    return ".".join(path.with_suffix("").parts)


def detect_streamlit_entry_points(file_map: dict[str, Path]) -> list[str]:
    """Find Python files that import Streamlit."""
    entry_points: list[str] = []

    for relative_path, absolute_path in sorted(file_map.items(), key=lambda item: item[0].lower()):
        if absolute_path.suffix.lower() != ".py" or not is_safe_text_file(absolute_path):
            continue

        text = safe_read_text(absolute_path)
        if re.search(r"^\s*(import|from)\s+streamlit\b", text, flags=re.MULTILINE | re.IGNORECASE):
            entry_points.append(relative_path)

    return entry_points


def add_general_setup_steps(repo_name: str, run_info: dict) -> None:
    """Add the always-present clone and change-directory steps."""
    add_unique(run_info["setup_steps"], "git clone <repo-url>")
    add_unique(run_info["setup_steps"], f"cd {repo_name}")


def detect_python_instructions(file_map: dict[str, Path], tech_stack: dict, run_info: dict) -> None:
    """Detect setup and run commands for Python-based projects."""
    requirements_path = get_preferred_path(file_map, "requirements.txt")
    pyproject_path = get_preferred_path(file_map, "pyproject.toml")
    pipfile_path = get_preferred_path(file_map, "Pipfile")
    app_path = get_preferred_path(file_map, "app.py")
    main_path = get_preferred_path(file_map, "main.py")
    streamlit_app_path = get_preferred_path(file_map, "streamlit_app.py")
    manage_path = get_preferred_path(file_map, "manage.py")

    if requirements_path:
        add_unique(run_info["setup_steps"], "pip install -r requirements.txt")

    if pyproject_path:
        add_unique(run_info["setup_steps"], "pip install .")

    if pipfile_path:
        add_unique(run_info["setup_steps"], "pipenv install")

    if app_path:
        add_unique(run_info["run_commands"], f"python {app_path}")
        add_unique(run_info["detected_entry_points"], app_path)

    if main_path:
        add_unique(run_info["run_commands"], f"python {main_path}")
        add_unique(run_info["detected_entry_points"], main_path)

    if streamlit_app_path:
        add_unique(run_info["run_commands"], f"streamlit run {streamlit_app_path}")
        add_unique(run_info["detected_entry_points"], streamlit_app_path)

    if manage_path:
        add_unique(run_info["run_commands"], f"python {manage_path} runserver")
        add_unique(run_info["detected_entry_points"], manage_path)

    for relative_path in detect_streamlit_entry_points(file_map):
        add_unique(run_info["run_commands"], f"streamlit run {relative_path}")
        add_unique(run_info["detected_entry_points"], relative_path)

    if "FastAPI" in tech_stack.get("frameworks", []):
        if main_path:
            module_path = module_path_from_relative_path(main_path)
            add_unique(run_info["run_commands"], f"uvicorn {module_path}:app --reload")
            add_unique(run_info["detected_entry_points"], main_path)
        elif app_path:
            module_path = module_path_from_relative_path(app_path)
            add_unique(run_info["run_commands"], f"uvicorn {module_path}:app --reload")
            add_unique(run_info["detected_entry_points"], app_path)


def detect_node_instructions(file_map: dict[str, Path], run_info: dict) -> None:
    """Detect Node and frontend setup/run commands."""
    package_json_path = get_preferred_path(file_map, "package.json")
    vite_config_path = get_preferred_path(file_map, "vite.config.js")

    if not package_json_path:
        return

    add_unique(run_info["setup_steps"], "npm install")

    package_scripts = read_package_json_scripts(file_map[package_json_path])
    has_vite_config = vite_config_path is not None

    if has_vite_config and "dev" in package_scripts:
        add_unique(run_info["run_commands"], "npm run dev")
        return

    if "dev" in package_scripts:
        add_unique(run_info["run_commands"], "npm run dev")
    elif "start" in package_scripts:
        add_unique(run_info["run_commands"], "npm start")
    elif "serve" in package_scripts:
        add_unique(run_info["run_commands"], "npm run serve")
    elif has_vite_config:
        add_unique(run_info["run_commands"], "npm run dev")


def detect_docker_instructions(repo_name: str, file_map: dict[str, Path], run_info: dict) -> None:
    """Detect Docker-related setup and run commands."""
    dockerfile_path = get_preferred_path(file_map, "Dockerfile")
    docker_compose_path = get_preferred_path(file_map, "docker-compose.yml")

    if dockerfile_path:
        add_unique(run_info["setup_steps"], f"docker build -t {repo_name} .")
        add_unique(run_info["run_commands"], f"docker run -p 5000:5000 {repo_name}")

    if docker_compose_path:
        add_unique(run_info["run_commands"], "docker compose up --build")


def detect_hardware_instructions(file_map: dict[str, Path], run_info: dict) -> None:
    """Detect notes and commands for Arduino and PlatformIO projects."""
    ino_files = [
        relative_path
        for relative_path, absolute_path in sorted(file_map.items(), key=lambda item: item[0].lower())
        if absolute_path.suffix.lower() == ".ino"
    ]

    for ino_file in ino_files:
        add_unique(run_info["detected_entry_points"], ino_file)

    if ino_files:
        add_unique(run_info["notes"], "Open the .ino file in Arduino IDE.")
        add_unique(run_info["notes"], "Install required board packages and libraries.")
        add_unique(run_info["notes"], "Select the correct board and port.")
        add_unique(run_info["notes"], "Upload the sketch.")

    platformio_path = get_preferred_path(file_map, "platformio.ini")
    if platformio_path:
        add_unique(run_info["setup_steps"], "pio run")
        add_unique(run_info["run_commands"], "pio run --target upload")
        add_unique(run_info["detected_entry_points"], platformio_path)


def detect_environment_and_database_notes(file_map: dict[str, Path], tech_stack: dict, run_info: dict) -> None:
    """Add helpful environment and database notes."""
    if get_preferred_path(file_map, ".env.example"):
        add_unique(
            run_info["notes"],
            "Create a .env file using .env.example before running the project.",
        )

    if any(database in DATABASE_NOTE_VALUES for database in tech_stack.get("databases", [])):
        add_unique(
            run_info["notes"],
            "Configure database credentials in environment variables before running.",
        )


def finalize_run_info(run_info: dict) -> dict:
    """Return the run instructions in a clean output shape."""
    return {
        "setup_steps": run_info["setup_steps"],
        "run_commands": run_info["run_commands"],
        "notes": run_info["notes"],
        "detected_entry_points": sorted(run_info["detected_entry_points"], key=str.lower),
    }


def detect_run_instructions(
    repo_path: str | Path,
    scan_result: dict | None = None,
    tech_stack: dict | None = None,
) -> dict:
    """
    Detect likely setup steps and run commands for a repository.

    The function is reusable on its own, but can also accept existing scan
    results to avoid scanning the same repo more than once.
    """
    root_path = validate_repo_path(repo_path)

    if scan_result is None:
        scan_result = scan_repository(
            root_path,
            include_tech_stack=False,
            include_run_instructions=False,
        )

    if tech_stack is None:
        tech_stack = detect_tech_stack(root_path, scan_result=scan_result)

    run_info = make_empty_run_info()
    file_map = get_file_map(root_path, scan_result)

    add_general_setup_steps(scan_result.get("repo_name", root_path.name), run_info)
    detect_python_instructions(file_map, tech_stack, run_info)
    detect_node_instructions(file_map, run_info)
    detect_docker_instructions(scan_result.get("repo_name", root_path.name), file_map, run_info)
    detect_hardware_instructions(file_map, run_info)
    detect_environment_and_database_notes(file_map, tech_stack, run_info)

    return finalize_run_info(run_info)


def format_run_instructions_for_markdown(run_info: dict) -> str:
    """Format the detected setup and run instructions as markdown."""
    sections: list[str] = []

    setup_steps = run_info.get("setup_steps", [])
    if setup_steps:
        setup_block = "\n".join(setup_steps)
        sections.append(f"## Setup Instructions\n\n```bash\n{setup_block}\n```")

    run_commands = run_info.get("run_commands", [])
    if run_commands:
        run_block = "\n".join(run_commands)
        sections.append(f"## Run Commands\n\n```bash\n{run_block}\n```")

    notes = run_info.get("notes", [])
    if notes:
        note_lines = "\n".join(f"- {note}" for note in notes)
        sections.append(f"## Notes\n\n{note_lines}")

    return "\n\n".join(sections)


def main() -> int:
    """Simple CLI entry point for testing run detection manually."""
    if len(sys.argv) != 2:
        print("Usage: python run_detector.py path/to/repo", file=sys.stderr)
        return 1

    try:
        result = detect_run_instructions(sys.argv[1])
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError, ValueError) as error:
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
