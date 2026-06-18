from __future__ import annotations

import argparse
import sys

from readme_generator import generate_and_save_readme
from tech_detector import format_tech_stack_for_markdown
from repo_health import analyze_repo_health, format_health_summary_for_cli


def print_cli_summary(result: dict) -> None:
    """Print a friendly summary after README generation finishes."""
    scan_result = result["scan_result"]
    tech_stack = result["tech_stack"]
    run_info = result["run_info"]
    save_result = result["save_result"]

    print(f"Repo name: {scan_result['repo_name']}")

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

    # Print repo health score
    from pathlib import Path
    health_result = analyze_repo_health(
        Path(scan_result["repo_path"]),
        scan_result=scan_result,
        tech_stack=tech_stack,
        run_info=run_info,
    )
    print(format_health_summary_for_cli(health_result))

    print(f"\nSaved file path: {save_result['saved_path']}")
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
    args = parser.parse_args()

    try:
        result = generate_and_save_readme(args.repo_path, overwrite=args.overwrite)
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    print_cli_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
