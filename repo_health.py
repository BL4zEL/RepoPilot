"""
Repo Health Score system for RepoPilot Lite.

Analyzes a scanned repository and returns a health score out of 100,
along with checks, strengths, issues, and suggestions.
"""

from __future__ import annotations

from pathlib import Path

from repo_scanner import validate_repo_path, scan_repository
from tech_detector import detect_tech_stack
from run_detector import detect_run_instructions


# Define all health checks with their points and conditions
HEALTH_CHECKS = [
    {
        "name": "README file",
        "points_possible": 15,
        "check_files": ["readme.md"],
        "message_pass": "README.md exists.",
        "message_fail": "No README.md found. Add one so GitHub visitors understand your project.",
    },
    {
        "name": "Dependency file",
        "points_possible": 15,
        "check_files": [
            "requirements.txt",
            "package.json",
            "pyproject.toml",
            "pipfile",
            "environment.yml",
            "pnpm-lock.yaml",
            "yarn.lock",
            "package-lock.json",
            "platformio.ini",
        ],
        "message_pass": "Dependency file found.",
        "message_fail": "No dependency file found. Add requirements.txt, package.json, or similar.",
    },
    {
        "name": "Clear entry point",
        "points_possible": 15,
        "check_files": [
            "app.py",
            "main.py",
            "streamlit_app.py",
            "manage.py",
            "index.html",
            "server.js",
            "index.js",
        ],
        "check_file_patterns": [
            lambda p: p.name.endswith(".ino"),
        ],
        "check_folder_files": [
            ("src", "main.jsx"),
            ("src", "main.tsx"),
            ("src", "App.jsx"),
            ("src", "App.tsx"),
        ],
        "message_pass": "Clear entry point found.",
        "message_fail": "No obvious entry point found. Add app.py, main.py, index.html, or document how to run the project.",
    },
    {
        "name": ".gitignore",
        "points_possible": 10,
        "check_files": [".gitignore"],
        "message_pass": ".gitignore exists.",
        "message_fail": "No .gitignore found. Add one to avoid committing unnecessary files.",
    },
    {
        "name": "License",
        "points_possible": 10,
        "check_files": ["license", "license.md", "licence", "licence.md"],
        "message_pass": "License file found.",
        "message_fail": "No license file found. Add a license if this is an open-source project.",
    },
    {
        "name": "Screenshots/assets",
        "points_possible": 10,
        "check_folders": [
            "assets",
            "screenshots",
            "docs/images",
            "public",
            "static",
            "images",
        ],
        "message_pass": "Assets or screenshots folder found.",
        "message_fail": "No screenshots or assets folder found. Add screenshots to make the repo look polished.",
    },
    {
        "name": "Tests",
        "points_possible": 10,
        "check_folders": ["tests", "test", "__tests__"],
        "check_file_prefixes": ["test_"],
        "check_file_suffixes": ["_test.py", ".test.js", ".spec.js", ".test.ts", ".spec.ts"],
        "message_pass": "Test files or test folder found.",
        "message_fail": "No tests found. Add basic tests to improve reliability.",
    },
    {
        "name": "Environment example",
        "points_possible": 5,
        "check_files": [
            ".env.example",
            "config.example.json",
            "config.example.py",
            "settings.example.py",
            "example.env",
        ],
        "message_pass": "Environment/config example found.",
        "message_fail": "No .env.example or config example found.",
    },
    {
        "name": "Project not empty",
        "points_possible": 5,
        "check_condition": "total_files_gt_1",
        "message_pass": "Project contains source files.",
        "message_fail": "Project looks empty.",
    },
    {
        "name": "Run instructions",
        "points_possible": 5,
        "check_condition": "run_commands_exist",
        "message_pass": "Run command detected.",
        "message_fail": "No run command could be detected.",
    },
]


def _check_files_exist(file_list: list[str], check_files: list[str]) -> bool:
    """Check if any of the check_files exist in the file list (case-insensitive)."""
    file_names_lower = {f.lower() for f in file_list}
    for check_file in check_files:
        if check_file.lower() in file_names_lower:
            return True
    return False


def _check_folder_exists(folder_list: list[str], check_folders: list[str]) -> bool:
    """Check if any of the check_folders exist in the folder list."""
    folder_names = {Path(f).name for f in folder_list}
    for check_folder in check_folders:
        if check_folder in folder_names:
            return True
    return False


def _check_entry_point_files(file_list: list[str], check_config: dict) -> bool:
    """Check for entry point files including patterns and nested paths."""
    file_names_lower = {f.lower(): f for f in file_list}
    
    # Check direct file matches
    for check_file in check_config.get("check_files", []):
        if check_file.lower() in file_names_lower:
            return True
    
    # Check .ino files
    for pattern_func in check_config.get("check_file_patterns", []):
        for file_path in file_list:
            if pattern_func(Path(file_path)):
                return True
    
    # Check nested files like src/main.jsx
    for folder, filename in check_config.get("check_folder_files", []):
        nested_path = f"{folder}/{filename}".lower()
        if nested_path in file_names_lower:
            return True
        # Also check with backslash on Windows-style paths
        nested_path_backslash = f"{folder}\\{filename}".lower()
        if nested_path_backslash in file_names_lower:
            return True
    
    return False


def _check_test_files(file_list: list[str], check_config: dict) -> bool:
    """Check for test files and folders."""
    # Check test folders
    if _check_folder_exists(
        [f for f in file_list if "/" not in f or f.split("/")[0] in check_config.get("check_folders", [])],
        check_config.get("check_folders", [])
    ):
        return True
    
    # More thorough folder check
    folder_names = set()
    for f in file_list:
        parts = Path(f).parts
        if len(parts) > 0:
            folder_names.add(parts[0])
    
    for check_folder in check_config.get("check_folders", []):
        if check_folder in folder_names:
            return True
    
    # Check file prefixes
    for prefix in check_config.get("check_file_prefixes", []):
        for file_path in file_list:
            if Path(file_path).name.startswith(prefix):
                return True
    
    # Check file suffixes
    for suffix in check_config.get("check_file_suffixes", []):
        for file_path in file_list:
            if Path(file_path).name.endswith(suffix):
                return True
    
    return False


def _evaluate_check(check_config: dict, scan_result: dict, run_info: dict | None) -> dict:
    """Evaluate a single health check and return the result."""
    file_list = scan_result.get("files", [])
    folder_list = scan_result.get("folders", [])
    total_files = scan_result.get("total_files", 0)
    
    passed = False
    check_condition = check_config.get("check_condition")
    
    if check_condition == "total_files_gt_1":
        passed = total_files > 1
    elif check_condition == "run_commands_exist":
        passed = bool(run_info and run_info.get("run_commands"))
    elif "check_folders" in check_config and "check_file_prefixes" in check_config:
        # This is the tests check
        passed = _check_test_files(file_list, check_config)
    elif "check_file_patterns" in check_config or "check_folder_files" in check_config:
        # This is the entry point check
        passed = _check_entry_point_files(file_list, check_config)
    elif "check_folders" in check_config:
        # Screenshots/assets check
        passed = _check_folder_exists(folder_list, check_config["check_folders"])
    elif "check_files" in check_config:
        # Standard file existence check
        passed = _check_files_exist(file_list, check_config["check_files"])
    
    points_awarded = check_config["points_possible"] if passed else 0
    
    return {
        "name": check_config["name"],
        "passed": passed,
        "points_awarded": points_awarded,
        "points_possible": check_config["points_possible"],
        "message": check_config["message_pass"] if passed else check_config["message_fail"],
    }


def _generate_suggestions_from_checks(checks: list[dict]) -> list[str]:
    """Generate suggestions based on failed checks."""
    suggestions = []
    seen_suggestions = set()
    
    suggestion_map = {
        "README file": "Generate a README using RepoPilot Lite and save it inside the repo.",
        "Dependency file": "Add a requirements.txt, package.json, or similar dependency file.",
        "Clear entry point": "Add a clear entry point like app.py, main.py, or index.html, or document how to run the project.",
        ".gitignore": "Add a .gitignore file to avoid committing unnecessary files.",
        "License": "Add an MIT License if this is an open-source project.",
        "Screenshots/assets": "Add screenshots under assets/screenshots/ and reference them in README.",
        "Tests": "Add a tests/ folder with basic test cases.",
        "Environment example": "Add a .env.example or config example file for environment variables.",
        "Project not empty": "Add more source files to the project.",
        "Run instructions": "Document how to run the project in the README.",
    }
    
    for check in checks:
        if not check["passed"]:
            suggestion = suggestion_map.get(check["name"])
            if suggestion and suggestion not in seen_suggestions:
                suggestions.append(suggestion)
                seen_suggestions.add(suggestion)
    
    return suggestions


def analyze_repo_health(
    repo_path: str | Path,
    scan_result: dict | None = None,
    tech_stack: dict | None = None,
    run_info: dict | None = None,
) -> dict:
    """
    Analyze a repository and return a health score with detailed feedback.
    
    Args:
        repo_path: Path to the repository to analyze.
        scan_result: Optional pre-computed scan result. If not provided, will be generated.
        tech_stack: Optional pre-computed tech stack. If not provided, will be generated.
        run_info: Optional pre-computed run info. If not provided, will be generated.
    
    Returns:
        A dictionary containing:
        - score: Total score out of 100
        - grade: Letter grade (A+, A, B, C, D, Needs Work)
        - checks: List of individual check results
        - strengths: List of passed check descriptions
        - issues: List of failed check descriptions
        - suggestions: List of improvement suggestions
    """
    root_path = validate_repo_path(repo_path)
    
    # Generate missing data if needed
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
    
    # Evaluate all checks
    checks = []
    for check_config in HEALTH_CHECKS:
        check_result = _evaluate_check(check_config, scan_result, run_info)
        checks.append(check_result)
    
    # Calculate total score
    total_score = sum(check["points_awarded"] for check in checks)
    max_score = sum(check["points_possible"] for check in checks)
    
    # Normalize to 100 if needed (should already be 100)
    score = min(100, total_score)
    
    # Determine grade
    if score >= 90:
        grade = "A+"
    elif score >= 80:
        grade = "A"
    elif score >= 70:
        grade = "B"
    elif score >= 60:
        grade = "C"
    elif score >= 50:
        grade = "D"
    else:
        grade = "Needs Work"
    
    # Generate strengths from passed checks
    strengths = [check["message"] for check in checks if check["passed"]]
    
    # Generate issues from failed checks
    issues = [check["message"] for check in checks if not check["passed"]]
    
    # Generate suggestions
    suggestions = _generate_suggestions_from_checks(checks)
    
    return {
        "score": score,
        "grade": grade,
        "checks": checks,
        "strengths": strengths,
        "issues": issues,
        "suggestions": suggestions,
    }


def format_health_summary_for_cli(health_result: dict) -> str:
    """Format health results for CLI output."""
    lines = []
    
    lines.append(f"\nRepo Health Score: {health_result['score']}/100")
    lines.append(f"Grade: {health_result['grade']}")
    
    # Passed checks summary
    passed_checks = [c for c in health_result["checks"] if c["passed"]]
    if passed_checks:
        lines.append("\nPassed:")
        for check in passed_checks:
            lines.append(f"- {check['name']}")
    
    # Issues summary
    failed_checks = [c for c in health_result["checks"] if not c["passed"]]
    if failed_checks:
        lines.append("\nNeeds improvement:")
        for check in failed_checks:
            lines.append(f"- {check['message']}")
    
    # Suggestions summary
    if health_result["suggestions"]:
        lines.append("\nSuggestions:")
        for suggestion in health_result["suggestions"]:
            lines.append(f"- {suggestion}")
    
    return "\n".join(lines)


def get_top_suggestions(health_result: dict, limit: int = 3) -> list[str]:
    """Get top N suggestions for README inclusion."""
    return health_result["suggestions"][:limit]


def format_health_section_for_readme(health_result: dict) -> str:
    """Format health suggestions as a markdown section for README."""
    suggestions = get_top_suggestions(health_result, limit=3)
    
    if not suggestions:
        return ""
    
    lines = ["\n## Repository Health Suggestions\n"]
    for suggestion in suggestions:
        lines.append(f"- {suggestion}")
    
    return "\n".join(lines) + "\n"
