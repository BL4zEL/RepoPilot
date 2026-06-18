from __future__ import annotations

from pathlib import Path

from repo_scanner import scan_repository, validate_repo_path
from run_detector import detect_run_instructions
from tech_detector import detect_tech_stack


CHECK_DEFINITIONS = {
    "readme": {
        "name": "README file",
        "points": 15,
        "pass_message": "README.md exists.",
        "fail_message": "No README.md found. Add one so GitHub visitors understand your project.",
        "strength": "Project has a README file.",
        "issue": "No README.md found.",
        "suggestion": "Generate a README using RepoPilot Lite and save it inside the repo.",
    },
    "dependency": {
        "name": "Dependency file",
        "points": 15,
        "pass_message": "Dependency file found.",
        "fail_message": "No dependency file found. Add requirements.txt, package.json, or similar.",
        "strength": "Project has a dependency file.",
        "issue": "No dependency file found.",
        "suggestion": "Add requirements.txt, package.json, or another dependency file.",
    },
    "entry_point": {
        "name": "Clear entry point",
        "points": 15,
        "pass_message": "Clear entry point found.",
        "fail_message": "No obvious entry point found. Add app.py, main.py, index.html, or document how to run the project.",
        "strength": "Project has a clear entry point.",
        "issue": "No obvious entry point found.",
        "suggestion": "Add app.py, main.py, index.html, or document how to run the project.",
    },
    "gitignore": {
        "name": ".gitignore file",
        "points": 10,
        "pass_message": ".gitignore exists.",
        "fail_message": "No .gitignore found. Add one to avoid committing unnecessary files.",
        "strength": "Project has a .gitignore file.",
        "issue": "No .gitignore found.",
        "suggestion": "Add a .gitignore file to avoid committing unnecessary files.",
    },
    "license": {
        "name": "License file",
        "points": 10,
        "pass_message": "License file found.",
        "fail_message": "No license file found. Add a license if this project is open-source.",
        "strength": "Project has a license file.",
        "issue": "No license file found.",
        "suggestion": "Add an MIT License if this is an open-source project.",
    },
    "assets": {
        "name": "Screenshots/assets folder",
        "points": 10,
        "pass_message": "Assets or screenshots folder found.",
        "fail_message": "No screenshots or assets folder found. Add screenshots to make the repo look polished.",
        "strength": "Project has an assets or screenshots folder.",
        "issue": "No screenshots/assets folder found.",
        "suggestion": "Add screenshots under assets/screenshots/ and reference them in README.",
    },
    "tests": {
        "name": "Tests",
        "points": 10,
        "pass_message": "Test files or test folder found.",
        "fail_message": "No tests found. Add basic tests to improve reliability.",
        "strength": "Project has tests.",
        "issue": "No tests found.",
        "suggestion": "Add a tests/ folder with basic test cases.",
    },
    "environment": {
        "name": "Environment example",
        "points": 5,
        "pass_message": "Environment/config example found.",
        "fail_message": "No .env.example or config example found.",
        "strength": "Project has an environment or config example.",
        "issue": "No .env.example or config example found.",
        "suggestion": "Add a .env.example or config.example file for local setup.",
    },
    "structure": {
        "name": "Project structure",
        "points": 5,
        "pass_message": "Project contains source files.",
        "fail_message": "Project looks empty.",
        "strength": "Project contains source files.",
        "issue": "Project looks empty.",
        "suggestion": "Add source files and organize the repo structure.",
    },
    "run_instructions": {
        "name": "Run instructions",
        "points": 5,
        "pass_message": "Run command detected.",
        "fail_message": "No run command could be detected.",
        "strength": "Project has detectable run instructions.",
        "issue": "No run command could be detected.",
        "suggestion": "Add a clear run command or startup script so contributors can launch the project easily.",
    },
}


DEPENDENCY_FILES = {
    "requirements.txt",
    "package.json",
    "pyproject.toml",
    "pipfile",
    "environment.yml",
    "pnpm-lock.yaml",
    "yarn.lock",
    "package-lock.json",
    "platformio.ini",
}

ENTRY_POINT_PATHS = {
    "app.py",
    "main.py",
    "streamlit_app.py",
    "manage.py",
    "index.html",
    "src/main.jsx",
    "src/main.tsx",
    "src/app.jsx",
    "src/app.tsx",
    "server.js",
    "index.js",
}

LICENSE_FILES = {
    "license",
    "license.md",
    "licence",
    "licence.md",
}

ASSET_FOLDERS = {
    "assets",
    "screenshots",
    "docs/images",
    "public",
    "static",
    "images",
}

TEST_FOLDERS = {
    "tests",
    "test",
    "__tests__",
}

ENVIRONMENT_FILES = {
    ".env.example",
    "config.example.json",
    "config.example.py",
    "settings.example.py",
    "example.env",
}


def make_file_index(scan_result: dict) -> tuple[set[str], set[str], set[str], set[str]]:
    """Build lowercase lookup sets from the scan results."""
    relative_files = {path.lower() for path in scan_result.get("files", [])}
    relative_folders = {path.lower() for path in scan_result.get("folders", [])}
    file_names = {Path(path).name.lower() for path in scan_result.get("files", [])}
    folder_names = {Path(path).name.lower() for path in scan_result.get("folders", [])}
    return relative_files, relative_folders, file_names, folder_names


def create_check_result(check_key: str, passed: bool) -> dict:
    """Create the public check dictionary for a health check."""
    definition = CHECK_DEFINITIONS[check_key]
    points_possible = definition["points"]

    return {
        "name": definition["name"],
        "passed": passed,
        "points_awarded": points_possible if passed else 0,
        "points_possible": points_possible,
        "message": definition["pass_message"] if passed else definition["fail_message"],
    }


def add_unique(items: list[str], value: str) -> None:
    """Add a value once while preserving the current order."""
    if value not in items:
        items.append(value)


def record_check_feedback(check_key: str, passed: bool, strengths: list[str], issues: list[str], suggestions: list[str]) -> None:
    """Turn a pass/fail result into strengths, issues, and suggestions."""
    definition = CHECK_DEFINITIONS[check_key]

    if passed:
        add_unique(strengths, definition["strength"])
        return

    add_unique(issues, definition["issue"])
    add_unique(suggestions, definition["suggestion"])


def has_test_files(relative_files: set[str]) -> bool:
    """Detect common test file naming patterns."""
    for relative_path in relative_files:
        file_name = Path(relative_path).name.lower()
        if file_name.startswith("test_"):
            return True
        if file_name.endswith("_test.py"):
            return True
        if file_name.endswith(".test.js") or file_name.endswith(".spec.js"):
            return True
        if file_name.endswith(".test.ts") or file_name.endswith(".spec.ts"):
            return True

    return False


def detect_readme(file_names: set[str]) -> bool:
    """Check whether a README file exists."""
    return "readme.md" in file_names


def detect_dependency_file(file_names: set[str]) -> bool:
    """Check whether a dependency file exists."""
    return any(file_name in DEPENDENCY_FILES for file_name in file_names)


def detect_entry_point(relative_files: set[str], file_names: set[str]) -> bool:
    """Check whether the repo has an obvious entry point."""
    if any(relative_path in ENTRY_POINT_PATHS for relative_path in relative_files):
        return True

    if any(file_name in {"app.py", "main.py", "streamlit_app.py", "manage.py", "index.html", "server.js", "index.js"} for file_name in file_names):
        return True

    return any(relative_path.endswith(".ino") for relative_path in relative_files)


def detect_assets_folder(relative_folders: set[str], folder_names: set[str]) -> bool:
    """Check whether a repo has a folder for screenshots or assets."""
    if any(folder_path in ASSET_FOLDERS for folder_path in relative_folders):
        return True

    return any(folder_name in {"assets", "screenshots", "public", "static", "images"} for folder_name in folder_names)


def detect_tests(relative_files: set[str], relative_folders: set[str], folder_names: set[str]) -> bool:
    """Check whether the repo contains tests."""
    if any(folder_path in TEST_FOLDERS for folder_path in relative_folders):
        return True

    if any(folder_name in TEST_FOLDERS for folder_name in folder_names):
        return True

    return has_test_files(relative_files)


def calculate_grade(score: int) -> str:
    """Convert a numeric score into a simple grade."""
    if score >= 90:
        return "A+"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    if score >= 50:
        return "D"
    return "Needs Work"


def analyze_repo_health(
    repo_path: str | Path,
    scan_result: dict | None = None,
    tech_stack: dict | None = None,
    run_info: dict | None = None,
) -> dict:
    """
    Analyze repository health and return a score, grade, and actionable feedback.

    The function safely reuses existing scan data when provided so other
    features can call it without repeating work.
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

    if run_info is None:
        run_info = detect_run_instructions(
            root_path,
            scan_result=scan_result,
            tech_stack=tech_stack,
        )

    relative_files, relative_folders, file_names, folder_names = make_file_index(scan_result)

    checks: list[dict] = []
    strengths: list[str] = []
    issues: list[str] = []
    suggestions: list[str] = []

    check_results = {
        "readme": detect_readme(file_names),
        "dependency": detect_dependency_file(file_names),
        "entry_point": detect_entry_point(relative_files, file_names),
        "gitignore": ".gitignore" in file_names,
        "license": any(file_name in LICENSE_FILES for file_name in file_names),
        "assets": detect_assets_folder(relative_folders, folder_names),
        "tests": detect_tests(relative_files, relative_folders, folder_names),
        "environment": any(file_name in ENVIRONMENT_FILES for file_name in file_names),
        "structure": scan_result.get("total_files", 0) > 1,
        "run_instructions": bool(run_info.get("run_commands")),
    }

    for check_key, passed in check_results.items():
        checks.append(create_check_result(check_key, passed))
        record_check_feedback(check_key, passed, strengths, issues, suggestions)

    score = sum(check["points_awarded"] for check in checks)
    grade = calculate_grade(score)

    return {
        "score": score,
        "grade": grade,
        "checks": checks,
        "strengths": strengths,
        "issues": issues,
        "suggestions": suggestions,
    }
