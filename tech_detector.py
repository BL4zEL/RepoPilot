from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from repo_scanner import scan_repository, validate_repo_path


MAX_READ_SIZE = 50 * 1024

# These file types are usually safe to read as text for lightweight detection.
SAFE_TEXT_SUFFIXES = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".cpp",
    ".cc",
    ".cxx",
    ".c",
    ".ino",
    ".java",
    ".ipynb",
    ".md",
    ".sql",
    ".txt",
    ".toml",
    ".json",
    ".yml",
    ".yaml",
    ".ini",
}

SAFE_TEXT_FILE_NAMES = {
    "dockerfile",
    "requirements.txt",
    "package.json",
    "pyproject.toml",
    "setup.py",
    "pipfile",
    "docker-compose.yml",
    ".env.example",
    ".gitignore",
    "license",
    "readme.md",
    "app.py",
    "main.py",
    "streamlit_app.py",
    "manage.py",
    "vite.config.js",
    "next.config.js",
    "platformio.ini",
}

LANGUAGE_RULES = {
    ".py": ["Python"],
    ".js": ["JavaScript"],
    ".jsx": ["JavaScript", "React JSX"],
    ".ts": ["TypeScript"],
    ".tsx": ["TypeScript", "React TSX"],
    ".html": ["HTML"],
    ".css": ["CSS"],
    ".cpp": ["C++"],
    ".cc": ["C++"],
    ".cxx": ["C++"],
    ".c": ["C"],
    ".ino": ["Arduino"],
    ".java": ["Java"],
    ".ipynb": ["Jupyter Notebook"],
    ".md": ["Markdown"],
    ".sql": ["SQL"],
}

PYTHON_TEXT_RULES = {
    "flask": ("frameworks", "Flask"),
    "streamlit": ("frameworks", "Streamlit"),
    "django": ("frameworks", "Django"),
    "fastapi": ("frameworks", "FastAPI"),
    "numpy": ("frameworks", "NumPy"),
    "pandas": ("frameworks", "Pandas"),
    "opencv-python": ("frameworks", "OpenCV"),
    "cv2": ("frameworks", "OpenCV"),
    "ultralytics": ("frameworks", "YOLO / Ultralytics"),
    "torch": ("frameworks", "PyTorch"),
    "tensorflow": ("frameworks", "TensorFlow"),
    "sklearn": ("frameworks", "Scikit-learn"),
    "scikit-learn": ("frameworks", "Scikit-learn"),
    "pymongo": ("databases", "MongoDB"),
    "firebase-admin": ("databases", "Firebase"),
}

PACKAGE_JSON_RULES = {
    "react": ("frameworks", "React"),
    "vite": ("tools", "Vite"),
    "next": ("frameworks", "Next.js"),
    "express": ("frameworks", "Express.js"),
    "tailwindcss": ("frameworks", "Tailwind CSS"),
    "typescript": ("languages", "TypeScript"),
    "vue": ("frameworks", "Vue"),
    "angular": ("frameworks", "Angular"),
    "mongoose": ("databases", "MongoDB"),
    "mongodb": ("databases", "MongoDB"),
    "firebase": ("databases", "Firebase"),
    "supabase": ("databases", "Supabase"),
    "pg": ("databases", "PostgreSQL"),
    "mysql": ("databases", "MySQL"),
}

TEXT_DATABASE_PATTERNS = {
    r"\bmongodb\b": "MongoDB",
    r"\bpymongo\b": "MongoDB",
    r"\bmongoose\b": "MongoDB",
    r"\bfirebase\b": "Firebase",
    r"\bsupabase\b": "Supabase",
    r"\bsqlite\b": "SQLite",
    r"\bpostgres(?:ql)?\b": "PostgreSQL",
    r"\bpsycopg2\b": "PostgreSQL",
    r"\bmysql\b": "MySQL",
}

HARDWARE_PATTERNS = {
    r"\besp32\b": "ESP32",
    r"\barduino\b": "Arduino",
    r"\braspe?berry\s*pi\b": "Raspberry Pi",
    r"\bjetson\b": "NVIDIA Jetson",
}

SPECIAL_FILE_RULES = {
    "dockerfile": ("tools", "Docker"),
    "docker-compose.yml": ("tools", "Docker Compose"),
    ".env.example": ("tools", "Environment Variables"),
    "requirements.txt": ("package_managers", "pip"),
    "package.json": ("package_managers", "npm"),
    "pyproject.toml": ("tools", "Python packaging"),
    "vite.config.js": ("tools", "Vite"),
    "next.config.js": ("tools", "Next.js"),
    "platformio.ini": ("tools", "PlatformIO"),
}


def make_empty_tech_stack() -> dict:
    """Create the default tech stack structure."""
    return {
        "languages": [],
        "frameworks": [],
        "tools": [],
        "databases": [],
        "hardware": [],
        "package_managers": [],
        "raw_detected_files": [],
    }


def add_value(tech_stack: dict, category: str, value: str) -> None:
    """Add a detected value while keeping the internal list unique."""
    if value not in tech_stack[category]:
        tech_stack[category].append(value)


def add_detected_file(raw_detected_files: set[str], relative_path: str) -> None:
    """Track which files contributed to detection."""
    raw_detected_files.add(relative_path)


def finalize_tech_stack(tech_stack: dict, raw_detected_files: set[str]) -> dict:
    """Return a clean, sorted output dictionary."""
    finalized = {}

    for key, values in tech_stack.items():
        if key == "raw_detected_files":
            continue
        finalized[key] = sorted(values, key=str.lower)

    finalized["raw_detected_files"] = sorted(raw_detected_files, key=str.lower)
    return finalized


def is_safe_text_file(file_path: Path) -> bool:
    """Check whether the file looks safe to read as text."""
    if file_path.name.lower() in SAFE_TEXT_FILE_NAMES:
        return True

    return file_path.suffix.lower() in SAFE_TEXT_SUFFIXES


def safe_read_text(file_path: Path, max_size: int = MAX_READ_SIZE) -> str:
    """
    Read a small chunk of a text file without crashing on encoding problems.

    Returning an empty string is fine for missing or unreadable files because
    detection should stay best-effort.
    """
    try:
        with file_path.open("r", encoding="utf-8", errors="ignore") as file_handle:
            return file_handle.read(max_size)
    except (OSError, UnicodeError):
        return ""


def get_file_map(repo_path: Path, scan_result: dict) -> dict[str, Path]:
    """Map repo-relative file paths to absolute file paths."""
    return {
        relative_path: repo_path / Path(relative_path)
        for relative_path in scan_result.get("files", [])
    }


def collect_candidate_files(repo_path: Path, scan_result: dict) -> dict[str, Path]:
    """
    Collect a focused set of files that are worth inspecting for tech detection.

    We prefer important files and common config files to keep the scan lightweight.
    """
    file_map = get_file_map(repo_path, scan_result)
    candidates: dict[str, Path] = {}

    for relative_path, absolute_path in file_map.items():
        file_name = absolute_path.name.lower()
        suffix = absolute_path.suffix.lower()

        if relative_path in scan_result.get("important_files", []):
            candidates[relative_path] = absolute_path
            continue

        if file_name in {
            "requirements.txt",
            "package.json",
            "pyproject.toml",
            ".env.example",
            "dockerfile",
            "docker-compose.yml",
            "platformio.ini",
        }:
            candidates[relative_path] = absolute_path
            continue

        if suffix == ".ino":
            candidates[relative_path] = absolute_path

    return candidates


def detect_languages_from_scan(scan_result: dict, tech_stack: dict) -> None:
    """Detect languages from the scanned file extensions."""
    for extension in scan_result.get("extensions", {}):
        for language in LANGUAGE_RULES.get(extension, []):
            add_value(tech_stack, "languages", language)


def apply_special_file_rules(relative_path: str, tech_stack: dict, raw_detected_files: set[str]) -> None:
    """Detect tools and package managers from well-known filenames."""
    file_name = Path(relative_path).name.lower()
    rule = SPECIAL_FILE_RULES.get(file_name)

    if not rule:
        return

    category, value = rule
    add_value(tech_stack, category, value)
    add_detected_file(raw_detected_files, relative_path)


def detect_hardware_from_file_path(relative_path: str, tech_stack: dict, raw_detected_files: set[str]) -> None:
    """Detect embedded projects from their file names alone."""
    if Path(relative_path).suffix.lower() == ".ino":
        add_value(tech_stack, "hardware", "Arduino")
        add_detected_file(raw_detected_files, relative_path)


def detect_from_plain_text(
    text: str,
    relative_path: str,
    tech_stack: dict,
    raw_detected_files: set[str],
) -> None:
    """Search text content for useful stack hints."""
    lower_text = text.lower()

    for keyword, (category, value) in PYTHON_TEXT_RULES.items():
        if keyword in lower_text:
            add_value(tech_stack, category, value)
            add_detected_file(raw_detected_files, relative_path)

    for pattern, value in TEXT_DATABASE_PATTERNS.items():
        if re.search(pattern, lower_text):
            add_value(tech_stack, "databases", value)
            add_detected_file(raw_detected_files, relative_path)

    for pattern, value in HARDWARE_PATTERNS.items():
        if re.search(pattern, lower_text):
            add_value(tech_stack, "hardware", value)
            add_detected_file(raw_detected_files, relative_path)


def detect_from_package_json(
    text: str,
    relative_path: str,
    tech_stack: dict,
    raw_detected_files: set[str],
) -> None:
    """Read package.json dependencies and map them to stack labels."""
    dependency_names: set[str] = set()

    try:
        package_data = json.loads(text)
    except json.JSONDecodeError:
        package_data = {}

    dependency_sections = [
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
    ]

    for section_name in dependency_sections:
        section_data = package_data.get(section_name, {})
        if isinstance(section_data, dict):
            dependency_names.update(name.lower() for name in section_data)

    if not dependency_names:
        return

    for package_name, (category, value) in PACKAGE_JSON_RULES.items():
        if package_name in dependency_names:
            add_value(tech_stack, category, value)
            add_detected_file(raw_detected_files, relative_path)


def detect_tech_stack(repo_path: str | Path, scan_result: dict | None = None) -> dict:
    """
    Detect the likely tech stack used in a repository.

    If scan_result is not provided, we reuse the repo scanner first so this
    function can be called directly from other files or from the CLI.
    """
    root_path = validate_repo_path(repo_path)

    if scan_result is None:
        scan_result = scan_repository(
            root_path,
            include_tech_stack=False,
            include_run_instructions=False,
        )

    tech_stack = make_empty_tech_stack()
    raw_detected_files: set[str] = set()

    detect_languages_from_scan(scan_result, tech_stack)

    for relative_path, absolute_path in collect_candidate_files(root_path, scan_result).items():
        apply_special_file_rules(relative_path, tech_stack, raw_detected_files)
        detect_hardware_from_file_path(relative_path, tech_stack, raw_detected_files)

        if not is_safe_text_file(absolute_path):
            continue

        text = safe_read_text(absolute_path)
        if not text:
            continue

        detect_from_plain_text(text, relative_path, tech_stack, raw_detected_files)

        if absolute_path.name.lower() == "package.json":
            detect_from_package_json(text, relative_path, tech_stack, raw_detected_files)

    return finalize_tech_stack(tech_stack, raw_detected_files)


def format_tech_stack_for_markdown(tech_stack: dict) -> str:
    """Format the detected stack as a compact markdown list."""
    label_map = [
        ("languages", "Languages"),
        ("frameworks", "Frameworks"),
        ("tools", "Tools"),
        ("databases", "Databases"),
        ("hardware", "Hardware"),
        ("package_managers", "Package Managers"),
    ]

    lines: list[str] = []

    for key, label in label_map:
        values = tech_stack.get(key, [])
        if values:
            lines.append(f"- {label}: {', '.join(values)}")

    return "\n".join(lines)


def main() -> int:
    """Simple CLI entry point for testing tech detection manually."""
    if len(sys.argv) != 2:
        print("Usage: python tech_detector.py path/to/repo", file=sys.stderr)
        return 1

    try:
        result = detect_tech_stack(sys.argv[1])
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
