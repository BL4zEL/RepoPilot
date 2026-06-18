from __future__ import annotations

import argparse
import sys

from readme_generator import generate_and_save_readme
from tech_detector import format_tech_stack_for_markdown


def get_ai_mode_status(file_analysis: dict | None, use_ai_requested: bool) -> str:
    """Translate file analysis limitations into a short AI status label."""
    if not use_ai_requested:
        return "disabled"

    if not file_analysis:
        return "fallback"

    limitation_text = " ".join(file_analysis.get("limitations", []))
    if "AI mode requested" in limitation_text or "AI enhancement failed" in limitation_text:
        return "fallback"

    return "enabled"


def print_cli_summary(result: dict) -> None:
    """Print a friendly summary after README generation finishes."""
    scan_result = result["scan_result"]
    tech_stack = result["tech_stack"]
    run_info = result["run_info"]
    repo_health = result.get("repo_health", {})
    file_analysis = result.get("file_analysis")
    save_result = result["save_result"]
    analyze_files_requested = result.get("analyze_files_requested", False)
    use_ai_requested = result.get("use_ai_requested", False)

    print(f"Repo name: {scan_result['repo_name']}")
    print(f"File understanding: {'enabled' if analyze_files_requested or use_ai_requested else 'disabled'}")
    print(f"AI mode: {get_ai_mode_status(file_analysis, use_ai_requested)}")

    tech_summary = format_tech_stack_for_markdown(tech_stack)
    print("Detected tech stack summary:")
    if tech_summary:
        print(tech_summary)
    else:
        print("- Not clearly detected yet.")

    print("Setup/run command summary:")
    if run_info.get("setup_steps"):
        print("Setup steps:")
        for step in run_info["setup_steps"]:
            print(f"- {step}")
    else:
        print("Setup steps:")
        print("- No setup steps detected.")

    if run_info.get("run_commands"):
        print("Run commands:")
        for command in run_info["run_commands"]:
            print(f"- {command}")
    else:
        print("Run commands:")
        print("- No run commands detected.")

    if run_info.get("notes"):
        print("Notes:")
        for note in run_info["notes"]:
            print(f"- {note}")

    if repo_health:
        print(f"Repo Health Score: {repo_health['score']}/100")
        print(f"Grade: {repo_health['grade']}")

        passed_checks = [check["name"] for check in repo_health.get("checks", []) if check.get("passed")]
        if passed_checks:
            print("Passed:")
            for check_name in passed_checks:
                print(f"- {check_name}")

        if repo_health.get("issues"):
            print("Needs improvement:")
            for issue in repo_health["issues"]:
                print(f"- {issue}")

        if repo_health.get("suggestions"):
            print("Suggestions:")
            for suggestion in repo_health["suggestions"]:
                print(f"- {suggestion}")

    print(f"Saved file path: {save_result['saved_path']}")
    print(save_result["message"])


def main() -> int:
    """Command-line entry point for RepoPilot Lite."""
    parser = argparse.ArgumentParser(
        description="Scan a local repository and safely generate a README file.",
    )
    parser.add_argument("repo_path", help="Path to the target repository folder.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing README.md instead of saving GENERATED_README.md.",
    )
    parser.add_argument(
        "--analyze-files",
        action="store_true",
        help="Analyze important project files for a deeper code explanation.",
    )
    parser.add_argument(
        "--use-ai",
        action="store_true",
        help="Use optional AI enhancement for file summaries. This also enables file analysis.",
    )
    args = parser.parse_args()

    try:
        result = generate_and_save_readme(
            args.repo_path,
            overwrite=args.overwrite,
            analyze_files=args.analyze_files or args.use_ai,
            use_ai=args.use_ai,
        )
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    result["analyze_files_requested"] = args.analyze_files or args.use_ai
    result["use_ai_requested"] = args.use_ai
    print_cli_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
