from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from file_understander import analyze_project_files
from repo_scanner import scan_repository, validate_repo_path
from run_detector import detect_run_instructions, format_run_instructions_for_markdown
from tech_detector import detect_tech_stack, format_tech_stack_for_markdown


def format_project_title(repo_name: str) -> str:
    """Convert a folder name into a nicer README title."""
    spaced_name = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", repo_name)
    cleaned_name = spaced_name.replace("-", " ").replace("_", " ").strip()
    words = [word for word in cleaned_name.split() if word]

    if not words:
        return "Project"

    return " ".join(word.capitalize() for word in words)


def generate_overview(tech_stack: dict) -> str:
    """Create a simple overview based on the detected project stack."""
    frameworks = set(tech_stack.get("frameworks", []))
    tools = set(tech_stack.get("tools", []))
    hardware = set(tech_stack.get("hardware", []))
    languages = set(tech_stack.get("languages", []))

    if "Streamlit" in frameworks:
        return "This project is a Streamlit-based Python application for interactive dashboards and data-driven workflows."

    if "Flask" in frameworks:
        return "This project is a Python Flask-based web application."

    if "FastAPI" in frameworks:
        return "This project is a Python FastAPI-based web application and API service."

    if "Django" in frameworks:
        return "This project is a Python Django-based web application."

    if "Next.js" in frameworks:
        return "This project is a Next.js web application."

    if "React" in frameworks and "Vite" in tools:
        return "This project is a React/Vite frontend application."

    if "React" in frameworks:
        return "This project is a React-based frontend application."

    if "Vue" in frameworks:
        return "This project is a Vue-based frontend application."

    if "Angular" in frameworks:
        return "This project is an Angular-based frontend application."

    if "Arduino" in hardware or "ESP32" in hardware or "Arduino" in languages:
        return "This project is an Arduino/embedded systems project."

    if "Python" in languages:
        return "This project is a Python software application."

    if "JavaScript" in languages or "TypeScript" in languages:
        return "This project contains source code and files for a web application."

    return "This project contains source code and files for a software application."


def build_feature_list(tech_stack: dict) -> list[str]:
    """Generate a practical feature list from detected project signals."""
    frameworks = set(tech_stack.get("frameworks", []))
    tools = set(tech_stack.get("tools", []))
    databases = set(tech_stack.get("databases", []))
    hardware = set(tech_stack.get("hardware", []))

    features: list[str] = []

    if frameworks.intersection({"Flask", "FastAPI", "Django", "Express.js"}):
        features.append("Web backend functionality")

    if frameworks.intersection({"React", "Next.js", "Vue", "Angular", "Tailwind CSS"}) or "Vite" in tools:
        features.append("Frontend interface")

    if "Streamlit" in frameworks:
        features.append("Interactive dashboard experience")

    if databases:
        features.append("Database integration")

    if frameworks.intersection({"OpenCV", "YOLO / Ultralytics", "PyTorch", "TensorFlow"}):
        features.append("AI and computer vision support")

    if hardware.intersection({"Arduino", "ESP32", "Raspberry Pi", "NVIDIA Jetson"}):
        features.append("Embedded hardware control")

    if "Docker" in tools or "Docker Compose" in tools:
        features.append("Containerized setup")

    features.append("Organized project structure")
    features.append("Easy local setup")

    return features


def format_features_for_markdown(features: list[str]) -> str:
    """Format feature items as markdown bullets."""
    return "\n".join(f"- {feature}" for feature in features)


def format_project_tree_for_markdown(scan_result: dict) -> str:
    """Return the repo tree section body."""
    project_tree = scan_result.get("project_tree", "")
    return project_tree or "Project structure could not be generated."


def load_readme_template() -> str:
    """Load the README template from the local templates folder."""
    template_path = Path(__file__).resolve().parent / "templates" / "readme_template.md"
    return template_path.read_text(encoding="utf-8")


def replace_template_values(template: str, values: dict[str, str]) -> str:
    """Replace simple placeholder tokens inside the README template."""
    rendered_template = template

    for key, value in values.items():
        rendered_template = rendered_template.replace(f"{{{{{key}}}}}", value)

    return rendered_template


def clean_markdown_spacing(markdown_text: str) -> str:
    """Remove extra blank lines left behind by optional sections."""
    lines = markdown_text.splitlines()
    cleaned_lines: list[str] = []
    previous_blank = False

    for line in lines:
        is_blank = not line.strip()
        if is_blank and previous_blank:
            continue

        cleaned_lines.append(line.rstrip())
        previous_blank = is_blank

    return "\n".join(cleaned_lines).strip() + "\n"


def format_repo_health_suggestions(repo_health: dict | None) -> str:
    """Create a small README section from the top repo health suggestions."""
    if not repo_health:
        return ""

    suggestions = repo_health.get("suggestions", [])[:3]
    if not suggestions:
        return ""

    suggestion_lines = "\n".join(f"- {suggestion}" for suggestion in suggestions)
    return f"## Repository Health Suggestions\n\n{suggestion_lines}\n"


def build_fallback_code_explanation(scan_result: dict, tech_stack: dict) -> str:
    """Create a simple explanation when file analysis is not enabled."""
    frameworks = set(tech_stack.get("frameworks", []))
    important_files = scan_result.get("important_files", [])

    if "Streamlit" in frameworks:
        project_logic = (
            "The project is organized around a Streamlit interface. The main UI file collects user input, "
            "shows results, and connects the frontend workflow to helper modules that do the backend processing."
        )
    elif "Flask" in frameworks:
        project_logic = (
            "The project follows a lightweight Flask structure. A main backend file likely starts the server, "
            "defines routes, and connects templates or API responses to supporting project logic."
        )
    elif "React" in frameworks or "Next.js" in frameworks:
        project_logic = (
            "The project is organized around frontend entry files and reusable interface logic. "
            "Main app files control the user interface flow, while supporting files provide behavior and styling."
        )
    elif any(file_path.endswith(".ino") for file_path in scan_result.get("files", [])):
        project_logic = (
            "The project is centered around firmware behavior. The main embedded file initializes hardware "
            "and repeatedly handles device logic such as sensors, relays, or connectivity."
        )
    else:
        project_logic = (
            "The project is organized around a few main source files and supporting configuration. "
            "These files work together to provide the application logic, setup, and runtime behavior."
        )

    important_preview = "\n".join(f"- `{Path(file_path).name}` is an important project file." for file_path in important_files[:5])
    if not important_preview:
        important_preview = "- Main source files and config files make up the core project structure."

    return (
        "## Beginner-Friendly Code Explanation\n\n"
        "### Project Logic\n\n"
        f"{project_logic}\n\n"
        "### Important Files\n\n"
        f"{important_preview}\n"
    )


def format_file_understanding_for_markdown(file_analysis: dict | None, max_files: int = 8) -> str:
    """Render the file understanding results as a README section."""
    if not file_analysis or not file_analysis.get("analyzed_files"):
        return ""

    lines = [
        "## Beginner-Friendly Code Explanation",
        "",
        "### Project Logic",
        "",
        file_analysis.get("project_logic_summary", "Project logic summary is not available."),
        "",
        "### Important Files",
        "",
    ]

    for file_info in file_analysis.get("analyzed_files", [])[:max_files]:
        lines.append(f"#### {file_info['path']}")
        lines.append(file_info["summary"])
        lines.append("")

        if file_info.get("detected_patterns"):
            lines.append("Detected:")
            for pattern in file_info["detected_patterns"]:
                lines.append(f"- {pattern}")
            lines.append("")

        functions_and_classes = []
        functions_and_classes.extend(file_info.get("important_functions", []))
        functions_and_classes.extend(file_info.get("important_classes", []))
        if functions_and_classes:
            lines.append("Functions / Classes:")
            for name in functions_and_classes[:10]:
                lines.append(f"- {name}")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def generate_readme(
    repo_path: str | Path,
    scan_result: dict | None = None,
    tech_stack: dict | None = None,
    run_info: dict | None = None,
    repo_health: dict | None = None,
    file_analysis: dict | None = None,
) -> str:
    """
    Generate a complete README markdown string for the given repository.

    The function reuses existing scan and detection results when they are
    provided so it can plug into the rest of RepoPilot Lite efficiently.
    """
    root_path = validate_repo_path(repo_path)

    if scan_result is None:
        scan_result = scan_repository(root_path)

    if tech_stack is None:
        tech_stack = scan_result.get("tech_stack") or detect_tech_stack(root_path, scan_result=scan_result)

    if run_info is None:
        run_info = scan_result.get("run_instructions") or detect_run_instructions(
            root_path,
            scan_result=scan_result,
            tech_stack=tech_stack,
        )

    if repo_health is None:
        from repo_health import analyze_repo_health

        repo_health = analyze_repo_health(
            root_path,
            scan_result=scan_result,
            tech_stack=tech_stack,
            run_info=run_info,
        )

    template = load_readme_template()
    project_title = format_project_title(scan_result.get("repo_name", root_path.name))
    overview = generate_overview(tech_stack)
    features = format_features_for_markdown(build_feature_list(tech_stack))
    tech_stack_markdown = format_tech_stack_for_markdown(tech_stack) or "- Not clearly detected yet."
    project_tree = format_project_tree_for_markdown(scan_result)
    run_instructions_markdown = format_run_instructions_for_markdown(run_info)

    rendered_readme = replace_template_values(
        template,
        {
            "project_title": project_title,
            "overview": overview,
            "features": features,
            "tech_stack": tech_stack_markdown,
            "project_tree": project_tree,
            "run_instructions": run_instructions_markdown,
        },
    )

    code_explanation = format_file_understanding_for_markdown(file_analysis)
    if not code_explanation:
        code_explanation = build_fallback_code_explanation(scan_result, tech_stack)

    rendered_readme = f"{rendered_readme.rstrip()}\n\n{code_explanation}"

    repo_health_suggestions = format_repo_health_suggestions(repo_health)
    if repo_health_suggestions:
        rendered_readme = f"{rendered_readme.rstrip()}\n\n{repo_health_suggestions}"

    return clean_markdown_spacing(rendered_readme)


def save_readme(
    markdown_text: str,
    repo_path: str | Path,
    overwrite: bool = False,
    output_name: str = "README.md",
) -> dict:
    """
    Save README content into the target repository with safe overwrite rules.

    If README.md already exists and overwrite is disabled, we keep the original
    file untouched and save the new content as GENERATED_README.md instead.
    """
    root_path = validate_repo_path(repo_path)

    if not markdown_text or not markdown_text.strip():
        raise ValueError("markdown_text cannot be empty.")

    target_path = root_path / output_name
    fallback_path = root_path / "GENERATED_README.md"
    target_existed_before_save = target_path.exists()

    if target_existed_before_save and not overwrite:
        fallback_path.write_text(markdown_text, encoding="utf-8")
        return {
            "saved_path": str(fallback_path),
            "filename": fallback_path.name,
            "overwritten": False,
            "message": f"{output_name} already existed. Saved generated README as {fallback_path.name} instead.",
        }

    target_path.write_text(markdown_text, encoding="utf-8")

    if target_existed_before_save and overwrite:
        message = f"{target_path.name} was overwritten successfully."
        overwritten = True
    else:
        message = f"{target_path.name} created successfully."
        overwritten = False

    return {
        "saved_path": str(target_path),
        "filename": target_path.name,
        "overwritten": overwritten,
        "message": message,
    }


def generate_and_save_readme(
    repo_path: str | Path,
    overwrite: bool = False,
    analyze_files: bool = False,
    use_ai: bool = False,
) -> dict:
    """Run the full offline README workflow and save the final file."""
    root_path = validate_repo_path(repo_path)
    target_readme_path = root_path / "README.md"
    readme_existed_before_save = target_readme_path.exists()

    scan_result = scan_repository(root_path)
    tech_stack = scan_result.get("tech_stack") or detect_tech_stack(root_path, scan_result=scan_result)
    run_info = scan_result.get("run_instructions") or detect_run_instructions(
        root_path,
        scan_result=scan_result,
        tech_stack=tech_stack,
    )
    from repo_health import analyze_repo_health

    repo_health = analyze_repo_health(
        root_path,
        scan_result=scan_result,
        tech_stack=tech_stack,
        run_info=run_info,
    )
    file_analysis = None
    if analyze_files or use_ai:
        file_analysis = analyze_project_files(
            root_path,
            scan_result=scan_result,
            tech_stack=tech_stack,
            use_ai=use_ai,
        )
    readme_preview = generate_readme(
        root_path,
        scan_result=scan_result,
        tech_stack=tech_stack,
        run_info=run_info,
        repo_health=repo_health,
        file_analysis=file_analysis,
    )
    save_result = save_readme(readme_preview, root_path, overwrite=overwrite)

    if save_result["filename"] == "README.md":
        save_result["overwritten"] = overwrite and readme_existed_before_save
        if save_result["overwritten"]:
            save_result["message"] = "README.md was overwritten."
        else:
            save_result["message"] = "README.md created successfully."

    return {
        "scan_result": scan_result,
        "tech_stack": tech_stack,
        "run_info": run_info,
        "repo_health": repo_health,
        "file_analysis": file_analysis,
        "readme_preview": readme_preview,
        "save_result": save_result,
    }


def main() -> int:
    """Simple CLI entry point for testing README generation manually."""
    parser = argparse.ArgumentParser(description="Generate README markdown for a local repository.")
    parser.add_argument("repo_path", help="Path to the target repository folder.")
    args = parser.parse_args()

    try:
        readme_text = generate_readme(args.repo_path)
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    try:
        print(readme_text, end="")
    except UnicodeEncodeError:
        print(readme_text.encode("ascii", errors="replace").decode("ascii"), end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
