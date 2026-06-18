from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from file_understander import analyze_project_files
from repo_scanner import scan_repository, validate_repo_path
from run_detector import detect_run_instructions
from tech_detector import detect_tech_stack, format_tech_stack_for_markdown


VALID_README_STYLES = {
    "basic": "basic",
    "detailed": "detailed",
    "beginner": "beginner",
    "beginner-friendly": "beginner",
    "portfolio": "portfolio",
    "portfolio showcase": "portfolio",
}

BEGINNER_TECH_EXPLANATIONS = {
    "Python": "used for the main application logic.",
    "JavaScript": "used for browser or frontend behavior.",
    "TypeScript": "used for JavaScript with stronger type checking.",
    "HTML": "used for page structure.",
    "CSS": "used for styling the interface.",
    "Flask": "used to build a lightweight Python web app.",
    "FastAPI": "used to build APIs and backend services.",
    "Django": "used for a full-featured Python web framework.",
    "Streamlit": "used to create interactive data apps quickly.",
    "React": "used to build component-based frontend interfaces.",
    "Next.js": "used for React apps with routing and production tooling.",
    "Vite": "used as a fast frontend development tool.",
    "Docker": "used to run the project in containers.",
    "Docker Compose": "used to run multiple services together.",
    "MongoDB": "used as a document database.",
    "PostgreSQL": "used as a relational database.",
    "MySQL": "used as a relational database.",
    "Firebase": "used for backend services such as auth or data storage.",
    "Supabase": "used for backend services and hosted databases.",
    "Arduino": "used for embedded hardware programming.",
    "ESP32": "used for Wi-Fi-enabled embedded hardware projects.",
    "PlatformIO": "used to build and upload embedded projects.",
    "pip": "used to install Python packages.",
    "npm": "used to install JavaScript packages.",
}

BEGINNER_STRUCTURE_EXPLANATIONS = {
    "app.py": "This is often the main Python entry file that starts the app.",
    "main.py": "This is often the main file that runs the project.",
    "requirements.txt": "This file lists Python packages the project needs.",
    "package.json": "This file lists Node.js packages and useful project scripts.",
    "templates": "This folder usually stores HTML page templates for backend web apps.",
    "static": "This folder usually stores CSS, JavaScript, images, or other frontend assets.",
    "src": "This folder usually contains the main source code for the project.",
    ".env.example": "This file shows which environment variables the project expects.",
    "tests": "This folder usually contains automated tests.",
}

GENERIC_FUTURE_IMPROVEMENTS = [
    "Add screenshots to make the project easier to understand at a glance.",
    "Add tests to improve confidence when changing the code.",
    "Add deployment instructions for production or cloud hosting.",
    "Add a license if you want to share the project publicly.",
    "Add a .env.example file for environment-based configuration.",
]


def normalize_readme_style(style: str | None) -> str:
    """Return a supported README style and fall back to detailed when needed."""
    if not style:
        return "detailed"

    cleaned_style = str(style).strip().lower()
    return VALID_README_STYLES.get(cleaned_style, "detailed")


def format_project_title(repo_name: str) -> str:
    """Convert a folder name into a clean README title."""
    spaced_name = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", repo_name)
    cleaned_name = spaced_name.replace("-", " ").replace("_", " ").strip()
    words = [word for word in cleaned_name.split() if word]

    if not words:
        return "Project"

    return " ".join(word.capitalize() for word in words)


def generate_overview(tech_stack: dict, beginner_mode: bool = False) -> str:
    """Create a short project overview from the detected stack."""
    frameworks = set(tech_stack.get("frameworks", []))
    tools = set(tech_stack.get("tools", []))
    hardware = set(tech_stack.get("hardware", []))
    languages = set(tech_stack.get("languages", []))

    if "Streamlit" in frameworks:
        if beginner_mode:
            return "This project appears to be a Python app built with Streamlit, which is commonly used to create interactive tools and dashboards."
        return "This project is a Streamlit-based Python application for interactive dashboards and data-driven workflows."

    if "Flask" in frameworks:
        if beginner_mode:
            return "This project appears to be a Python web application built with Flask."
        return "This project is a Python Flask-based web application."

    if "FastAPI" in frameworks:
        if beginner_mode:
            return "This project appears to be a Python backend project built with FastAPI for APIs or web services."
        return "This project is a Python FastAPI-based web application and API service."

    if "Django" in frameworks:
        if beginner_mode:
            return "This project appears to be a Django web application with structured backend features."
        return "This project is a Python Django-based web application."

    if "Next.js" in frameworks:
        return "This project appears to be a Next.js web application." if beginner_mode else "This project is a Next.js web application."

    if "React" in frameworks and "Vite" in tools:
        if beginner_mode:
            return "This project appears to be a frontend web app built with React and Vite."
        return "This project is a React/Vite frontend application."

    if "React" in frameworks:
        return "This project appears to be a React-based frontend application." if beginner_mode else "This project is a React-based frontend application."

    if "Vue" in frameworks:
        return "This project appears to be a Vue-based frontend application." if beginner_mode else "This project is a Vue-based frontend application."

    if "Angular" in frameworks:
        return "This project appears to be an Angular-based frontend application." if beginner_mode else "This project is an Angular-based frontend application."

    if "Arduino" in hardware or "ESP32" in hardware or "Arduino" in languages:
        if beginner_mode:
            return "This project appears to be an embedded or Arduino-style project that interacts with hardware."
        return "This project is an Arduino or embedded systems project."

    if "Python" in languages:
        return "This project appears to be a Python application." if beginner_mode else "This project is a Python software application."

    if "JavaScript" in languages or "TypeScript" in languages:
        return "This project appears to contain source code for a web application." if beginner_mode else "This project contains source code and files for a web application."

    return "This project contains source code and files for a software application."


def generate_what_project_does(tech_stack: dict) -> str:
    """Explain the project in simple, beginner-focused language."""
    frameworks = set(tech_stack.get("frameworks", []))
    hardware = set(tech_stack.get("hardware", []))
    languages = set(tech_stack.get("languages", []))

    if "Streamlit" in frameworks:
        return "It lets a user open an interactive interface, provide input, and see results directly in the browser."

    if frameworks.intersection({"Flask", "FastAPI", "Django", "Express.js"}):
        return "It appears to run backend logic, respond to requests, and connect application code to web routes or APIs."

    if frameworks.intersection({"React", "Next.js", "Vue", "Angular"}):
        return "It appears to provide a user-facing frontend interface that runs in the browser."

    if hardware.intersection({"Arduino", "ESP32", "Raspberry Pi", "NVIDIA Jetson"}) or "Arduino" in languages:
        return "It appears to control hardware behavior such as sensors, pins, connectivity, or device actions."

    if "Python" in languages:
        return "It appears to run Python-based application logic using one or more main source files."

    return "It appears to contain the code and configuration needed to run a software project locally."


def build_feature_list(tech_stack: dict) -> list[str]:
    """Generate a safe feature list from detected project signals."""
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


def build_license_section(scan_result: dict) -> str:
    """Create a short license section whether or not a license file exists."""
    file_names = {Path(file_path).name.lower() for file_path in scan_result.get("files", [])}

    if "license" in file_names or "license.md" in file_names:
        body = "See the repository license file for usage and distribution terms."
    else:
        body = "Add a license such as MIT if you plan to share this project publicly."

    return build_text_section("License", body)


def build_section_lines(title: str, lines: list[str]) -> str:
    """Build a markdown section from a list of text lines."""
    cleaned_lines = [line for line in lines if line.strip()]
    if not cleaned_lines:
        return ""
    return f"## {title}\n\n" + "\n".join(cleaned_lines).strip() + "\n"


def build_text_section(title: str, body: str) -> str:
    """Build a markdown section from a plain text body."""
    if not body or not body.strip():
        return ""
    return f"## {title}\n\n{body.strip()}\n"


def build_bullet_section(title: str, items: list[str]) -> str:
    """Build a markdown bullet list section."""
    cleaned_items = [item.strip() for item in items if item and item.strip()]
    if not cleaned_items:
        return ""
    return build_section_lines(title, [f"- {item}" for item in cleaned_items])


def build_code_section(title: str, items: list[str], language: str = "bash") -> str:
    """Build a fenced code block section from command lines."""
    cleaned_items = [item.rstrip() for item in items if item and item.strip()]
    if not cleaned_items:
        return ""
    body = "\n".join(cleaned_items)
    return f"## {title}\n\n```{language}\n{body}\n```\n"


def build_project_structure_section(scan_result: dict) -> str:
    """Build a markdown-friendly project tree section."""
    project_tree = scan_result.get("project_tree", "").strip()
    if not project_tree:
        project_tree = "Project structure could not be generated."
    return f"## Project Structure\n\n```text\n{project_tree}\n```\n"


def build_notes_section(run_info: dict) -> str:
    """Build a notes section from detected run information."""
    return build_bullet_section("Notes", run_info.get("notes", []))


def build_tech_stack_section(tech_stack: dict) -> str:
    """Build the normal tech stack section."""
    tech_stack_markdown = format_tech_stack_for_markdown(tech_stack) or "- Not clearly detected yet."
    return build_text_section("Tech Stack", tech_stack_markdown)


def build_beginner_tech_stack_section(tech_stack: dict) -> str:
    """Build a tech stack section with simple explanations for beginners."""
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
        if not values:
            continue
        lines.append(f"### {label}")
        lines.append("")
        for value in values:
            explanation = BEGINNER_TECH_EXPLANATIONS.get(value, "used somewhere in this project.")
            lines.append(f"- **{value}**: {explanation}")
        lines.append("")

    if not lines:
        return build_text_section("Tech Stack", "No major tech stack was clearly detected yet.")

    return build_section_lines("Tech Stack", lines)


def format_repo_health_suggestions(
    health_report: dict | None,
    beginner_mode: bool = False,
    include_when_score_below: int | None = None,
) -> str:
    """Build a small health suggestions section from repo health data."""
    if not health_report:
        return ""

    score = health_report.get("score")
    if include_when_score_below is not None and isinstance(score, int) and score >= include_when_score_below:
        return ""

    suggestions = health_report.get("suggestions", [])[:3]
    if not suggestions:
        return ""

    if beginner_mode:
        lines = [
            f"- {suggestion} This makes the repo easier for new developers to understand and run."
            for suggestion in suggestions
        ]
    else:
        lines = [f"- {suggestion}" for suggestion in suggestions]

    return build_section_lines("Repository Health Suggestions", lines)


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

    important_preview = [
        f"- `{Path(file_path).name}` is an important project file."
        for file_path in important_files[:5]
    ]
    if not important_preview:
        important_preview = ["- Main source files and config files make up the core project structure."]

    lines = [
        "## Beginner-Friendly Code Explanation",
        "",
        "### Project Logic",
        "",
        project_logic,
        "",
        "### Important Files",
        "",
        *important_preview,
        "",
    ]
    return "\n".join(lines).strip() + "\n"


def format_file_understanding_for_markdown(
    file_analysis: dict | None,
    max_files: int = 8,
    simple_mode: bool = False,
    summary_only: bool = False,
) -> str:
    """Render file analysis results as markdown sections."""
    if not file_analysis:
        return ""

    project_logic_summary = file_analysis.get("project_logic_summary", "").strip()
    analyzed_files = file_analysis.get("analyzed_files", [])

    if not project_logic_summary and not analyzed_files:
        return ""

    if summary_only:
        if not project_logic_summary:
            return ""
        return build_text_section("Project Logic Summary", project_logic_summary)

    lines = [
        "## Beginner-Friendly Code Explanation",
        "",
        "### Project Logic",
        "",
        project_logic_summary or "Project logic summary is not available.",
        "",
        "### Important Files",
        "",
    ]

    limited_files = analyzed_files[:max_files]
    if not limited_files:
        lines.append("- No important files were analyzed.")
        lines.append("")
        return "\n".join(lines).strip() + "\n"

    for file_info in limited_files:
        lines.append(f"#### {file_info['path']}")
        lines.append(file_info.get("summary", "Summary is not available."))
        lines.append("")

        detected_patterns = file_info.get("detected_patterns", [])
        if detected_patterns and not simple_mode:
            lines.append("Detected:")
            for pattern in detected_patterns:
                lines.append(f"- {pattern}")
            lines.append("")

        if not simple_mode:
            functions_and_classes = []
            functions_and_classes.extend(file_info.get("important_functions", []))
            functions_and_classes.extend(file_info.get("important_classes", []))
            if functions_and_classes:
                lines.append("Functions / Classes:")
                for name in functions_and_classes[:10]:
                    lines.append(f"- {name}")
                lines.append("")

    return "\n".join(lines).strip() + "\n"


def build_code_explanation_section(scan_result: dict, tech_stack: dict, file_analysis: dict | None, readme_style: str) -> str:
    """Choose the right level of code explanation for the current style."""
    if readme_style == "basic":
        return ""

    if readme_style == "portfolio":
        explanation = format_file_understanding_for_markdown(file_analysis, summary_only=True)
        if explanation:
            return explanation
        fallback = build_fallback_code_explanation(scan_result, tech_stack)
        project_logic_match = re.search(
            r"### Project Logic\s+(.*?)\s+### Important Files",
            fallback,
            flags=re.DOTALL,
        )
        if project_logic_match:
            return build_text_section("Project Logic Summary", project_logic_match.group(1).strip())
        return ""

    if readme_style == "beginner":
        explanation = format_file_understanding_for_markdown(
            file_analysis,
            max_files=10,
            simple_mode=True,
        )
        return explanation or build_fallback_code_explanation(scan_result, tech_stack)

    explanation = format_file_understanding_for_markdown(file_analysis, max_files=8)
    return explanation or build_fallback_code_explanation(scan_result, tech_stack)


def generate_beginner_notes(scan_result: dict, tech_stack: dict, run_info: dict) -> list[str]:
    """Generate simple notes that help beginners understand the repo."""
    file_names = {Path(file_path).name for file_path in scan_result.get("files", [])}
    folder_names = {Path(folder_path).name for folder_path in scan_result.get("folders", [])}
    notes: list[str] = []

    if "requirements.txt" in file_names:
        notes.append("`requirements.txt` lists the Python packages you need to install before running the project.")

    if "package.json" in file_names:
        notes.append("`package.json` lists JavaScript packages and project scripts such as development or start commands.")

    if "app.py" in file_names:
        notes.append("`app.py` is often the main Python file that starts the application.")
    elif "main.py" in file_names:
        notes.append("`main.py` is often the main file used to run the project.")

    if "templates" in folder_names:
        notes.append("The `templates` folder usually stores HTML files used by backend web frameworks.")

    if "static" in folder_names:
        notes.append("The `static` folder usually stores CSS, JavaScript, images, or other frontend assets.")

    if "src" in folder_names:
        notes.append("The `src` folder usually contains the main source code for the project.")

    if ".env.example" in file_names:
        notes.append("Environment variables let you keep secrets and machine-specific settings out of the main source code.")

    if "Python" in tech_stack.get("languages", []) or "pip" in tech_stack.get("package_managers", []):
        notes.append("A virtual environment is helpful for keeping this project's Python packages separate from other projects.")

    if run_info.get("notes"):
        for note in run_info["notes"]:
            if note not in notes:
                notes.append(note)

    return notes


def build_beginner_structure_explanations(scan_result: dict) -> str:
    """Explain common files and folders shown in the repo structure."""
    lines: list[str] = []
    seen_names: set[str] = set()

    ordered_names = scan_result.get("top_level_files", []) + scan_result.get("top_level_folders", [])
    for name in ordered_names:
        if name in seen_names:
            continue
        explanation = BEGINNER_STRUCTURE_EXPLANATIONS.get(name)
        if explanation:
            lines.append(f"- **{name}**: {explanation}")
            seen_names.add(name)

    if not lines:
        return ""

    return build_section_lines("Project Structure Guide", lines)


def generate_what_i_learned(tech_stack: dict, scan_result: dict) -> list[str]:
    """Generate a safe 'What I Learned' list for portfolio mode."""
    frameworks = set(tech_stack.get("frameworks", []))
    tools = set(tech_stack.get("tools", []))
    languages = set(tech_stack.get("languages", []))
    hardware = set(tech_stack.get("hardware", []))
    learned: list[str] = []

    if "Flask" in frameworks:
        learned.extend(
            [
                "Building Python web routes.",
                "Connecting backend logic with frontend templates.",
                "Managing dependencies with requirements.txt.",
            ]
        )

    if "React" in frameworks:
        learned.extend(
            [
                "Creating component-based frontend interfaces.",
                "Structuring frontend code for reuse and readability.",
                "Running frontend development scripts locally.",
            ]
        )

    if "Vite" in tools:
        learned.append("Using modern frontend tooling for fast local development.")

    if "Streamlit" in frameworks:
        learned.extend(
            [
                "Building interactive Python interfaces quickly.",
                "Connecting UI controls to backend processing logic.",
            ]
        )

    if "FastAPI" in frameworks:
        learned.extend(
            [
                "Designing Python API endpoints.",
                "Organizing backend logic around request and response flow.",
            ]
        )

    if hardware.intersection({"Arduino", "ESP32", "Raspberry Pi", "NVIDIA Jetson"}) or "Arduino" in languages:
        learned.extend(
            [
                "Working with embedded firmware structure.",
                "Using `setup()` and `loop()` style program flow.",
                "Interacting with hardware pins, sensors, or connectivity modules.",
            ]
        )

    if "Docker" in tools:
        learned.append("Packaging the project with container-based workflows.")

    if not learned:
        learned.extend(
            [
                "Organizing a project into clear source files and configuration.",
                "Documenting setup and usage so the repo is easier to share.",
            ]
        )

    unique_learned: list[str] = []
    for item in learned:
        if item not in unique_learned:
            unique_learned.append(item)

    return unique_learned[:6]


def generate_project_tagline(repo_name: str, tech_stack: dict) -> str:
    """Generate a short, polished tagline for portfolio mode."""
    frameworks = set(tech_stack.get("frameworks", []))
    tools = set(tech_stack.get("tools", []))
    hardware = set(tech_stack.get("hardware", []))
    project_title = format_project_title(repo_name)

    if "Streamlit" in frameworks:
        return f"A polished Streamlit project focused on interactive Python workflows in {project_title}."
    if "Flask" in frameworks:
        return f"A lightweight Flask application structured for clear backend development in {project_title}."
    if "React" in frameworks and "Vite" in tools:
        return f"A modern React and Vite frontend project for clean local development in {project_title}."
    if "Next.js" in frameworks:
        return f"A production-friendly Next.js project built for a polished web experience in {project_title}."
    if hardware.intersection({"Arduino", "ESP32", "Raspberry Pi", "NVIDIA Jetson"}):
        return f"An embedded systems project focused on practical hardware control in {project_title}."
    return f"A clean software project with organized structure and reproducible local setup in {project_title}."


def build_future_improvements(scan_result: dict, health_report: dict | None, readme_style: str) -> list[str]:
    """Generate safe future improvement ideas without inventing project features."""
    if readme_style == "basic":
        return []

    suggestions: list[str] = []
    if health_report:
        for suggestion in health_report.get("suggestions", []):
            if suggestion not in suggestions:
                suggestions.append(suggestion)

    file_names = {Path(file_path).name.lower() for file_path in scan_result.get("files", [])}
    all_paths_lower = {file_path.lower() for file_path in scan_result.get("files", [])}

    for fallback in GENERIC_FUTURE_IMPROVEMENTS:
        if "screenshot" in fallback.lower() and any("screenshot" in path for path in all_paths_lower):
            continue
        if "tests" in fallback.lower() and any("test" in Path(path).name.lower() for path in all_paths_lower):
            continue
        if ".env.example" in fallback.lower() and ".env.example" in file_names:
            continue
        if "license" in fallback.lower() and ("license" in file_names or "license.md" in file_names):
            continue
        if fallback not in suggestions:
            suggestions.append(fallback)

    return suggestions[:5]


def load_readme_template(style: str) -> str:
    """Load a README template file for the selected style."""
    normalized_style = normalize_readme_style(style)
    template_path = Path(__file__).resolve().parent / "templates" / f"readme_{normalized_style}.md"
    return template_path.read_text(encoding="utf-8")


def replace_template_values(template: str, values: dict[str, str]) -> str:
    """Replace simple placeholder tokens inside a README template."""
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


def build_readme_values(
    root_path: Path,
    scan_result: dict,
    tech_stack: dict,
    run_info: dict,
    health_report: dict | None,
    file_analysis: dict | None,
    readme_style: str,
) -> dict[str, str]:
    """Build placeholder values used by all README templates."""
    normalized_style = normalize_readme_style(readme_style)
    project_title = format_project_title(scan_result.get("repo_name", root_path.name))
    overview_text = generate_overview(tech_stack, beginner_mode=normalized_style == "beginner")
    features = build_feature_list(tech_stack)
    future_improvements = build_future_improvements(scan_result, health_report, normalized_style)
    code_explanation = build_code_explanation_section(scan_result, tech_stack, file_analysis, normalized_style)

    values = {
        "project_title": project_title,
        "tagline": generate_project_tagline(scan_result.get("repo_name", root_path.name), tech_stack),
        "overview_section": build_text_section("Overview", overview_text),
        "what_project_does_section": build_text_section("What This Project Does", generate_what_project_does(tech_stack)),
        "features_section": build_bullet_section("Features", features),
        "key_features_section": build_bullet_section("Key Features", features),
        "tech_stack_section": build_tech_stack_section(tech_stack),
        "beginner_tech_stack_section": build_beginner_tech_stack_section(tech_stack),
        "project_structure_section": build_project_structure_section(scan_result),
        "project_structure_guide_section": build_beginner_structure_explanations(scan_result),
        "setup_section": build_code_section("Setup Instructions", run_info.get("setup_steps", [])),
        "installation_section": build_code_section("Installation", run_info.get("setup_steps", [])),
        "run_section": build_code_section("How to Run", run_info.get("run_commands", [])),
        "usage_section": build_code_section("Usage", run_info.get("run_commands", [])),
        "notes_section": build_notes_section(run_info),
        "screenshots_section": build_text_section("Screenshots", "Add screenshots or GIFs here to show the project in action."),
        "demo_section": build_text_section("Demo / Screenshots", "Add screenshots, screen recordings, or a live demo link here."),
        "code_explanation_section": code_explanation,
        "beginner_notes_section": build_bullet_section(
            "Common Beginner Notes",
            generate_beginner_notes(scan_result, tech_stack, run_info),
        ),
        "future_improvements_section": build_bullet_section("Future Improvements", future_improvements),
        "learned_section": build_bullet_section("What I Learned", generate_what_i_learned(tech_stack, scan_result)),
        "repo_health_section": format_repo_health_suggestions(
            health_report,
            beginner_mode=normalized_style == "beginner",
            include_when_score_below=50 if normalized_style == "basic" else None,
        ),
        "license_section": build_license_section(scan_result),
    }
    return values


def generate_basic_readme(
    repo_path: Path,
    scan_result: dict,
    tech_stack: dict,
    run_info: dict,
    health_report: dict | None,
    file_analysis: dict | None,
) -> str:
    """Generate a short README for simple repositories."""
    template = load_readme_template("basic")
    values = build_readme_values(
        repo_path,
        scan_result,
        tech_stack,
        run_info,
        health_report,
        file_analysis,
        "basic",
    )
    return replace_template_values(template, values)


def generate_detailed_readme(
    repo_path: Path,
    scan_result: dict,
    tech_stack: dict,
    run_info: dict,
    health_report: dict | None,
    file_analysis: dict | None,
) -> str:
    """Generate the default RepoPilot Lite README."""
    template = load_readme_template("detailed")
    values = build_readme_values(
        repo_path,
        scan_result,
        tech_stack,
        run_info,
        health_report,
        file_analysis,
        "detailed",
    )
    return replace_template_values(template, values)


def generate_beginner_readme(
    repo_path: Path,
    scan_result: dict,
    tech_stack: dict,
    run_info: dict,
    health_report: dict | None,
    file_analysis: dict | None,
) -> str:
    """Generate a beginner-friendly README with extra explanations."""
    template = load_readme_template("beginner")
    values = build_readme_values(
        repo_path,
        scan_result,
        tech_stack,
        run_info,
        health_report,
        file_analysis,
        "beginner",
    )
    return replace_template_values(template, values)


def generate_portfolio_readme(
    repo_path: Path,
    scan_result: dict,
    tech_stack: dict,
    run_info: dict,
    health_report: dict | None,
    file_analysis: dict | None,
) -> str:
    """Generate a polished portfolio-style README."""
    template = load_readme_template("portfolio")
    values = build_readme_values(
        repo_path,
        scan_result,
        tech_stack,
        run_info,
        health_report,
        file_analysis,
        "portfolio",
    )
    return replace_template_values(template, values)


def generate_readme(
    repo_path: str | Path,
    scan_result: dict | None = None,
    tech_stack: dict | None = None,
    run_info: dict | None = None,
    health_report: dict | None = None,
    file_analysis: dict | None = None,
    readme_style: str = "detailed",
    repo_health: dict | None = None,
) -> str:
    """
    Generate a README markdown string for the given repository.

    The function keeps detection logic reusable by accepting existing scan and
    analysis results when they are already available.
    """
    root_path = validate_repo_path(repo_path)
    selected_style = normalize_readme_style(readme_style)

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

    if health_report is None:
        health_report = repo_health

    if health_report is None:
        from repo_health import analyze_repo_health

        health_report = analyze_repo_health(
            root_path,
            scan_result=scan_result,
            tech_stack=tech_stack,
            run_info=run_info,
        )

    if selected_style == "basic":
        rendered_readme = generate_basic_readme(
            root_path,
            scan_result,
            tech_stack,
            run_info,
            health_report,
            file_analysis,
        )
    elif selected_style == "beginner":
        rendered_readme = generate_beginner_readme(
            root_path,
            scan_result,
            tech_stack,
            run_info,
            health_report,
            file_analysis,
        )
    elif selected_style == "portfolio":
        rendered_readme = generate_portfolio_readme(
            root_path,
            scan_result,
            tech_stack,
            run_info,
            health_report,
            file_analysis,
        )
    else:
        rendered_readme = generate_detailed_readme(
            root_path,
            scan_result,
            tech_stack,
            run_info,
            health_report,
            file_analysis,
        )

    return clean_markdown_spacing(rendered_readme)


def build_outputs_readme_path(output_directory: Path, repo_name: str, readme_style: str, overwrite: bool) -> tuple[Path, bool]:
    """Build a safe output path for the shared outputs folder."""
    base_name = f"{repo_name}_{normalize_readme_style(readme_style)}_README"
    target_path = output_directory / f"{base_name}.md"
    existed = target_path.exists()

    if overwrite or not existed:
        return target_path, existed

    index = 1
    while True:
        candidate_path = output_directory / f"{base_name}_{index}.md"
        if not candidate_path.exists():
            return candidate_path, False
        index += 1


def save_readme(
    markdown_text: str,
    repo_path: str | Path,
    overwrite: bool = False,
    output_name: str = "README.md",
    save_location: str = "repo",
    readme_style: str = "detailed",
) -> dict:
    """
    Save README content either inside the target repo or into the shared outputs folder.

    Repo mode keeps the previous safe behavior. Outputs mode writes a style-aware
    filename such as outputs/project_detailed_README.md.
    """
    root_path = validate_repo_path(repo_path)

    if not markdown_text or not markdown_text.strip():
        raise ValueError("markdown_text cannot be empty.")

    normalized_location = str(save_location).strip().lower()
    if normalized_location not in {"repo", "outputs"}:
        raise ValueError("save_location must be either 'repo' or 'outputs'.")

    if normalized_location == "outputs":
        output_directory = Path(__file__).resolve().parent / "outputs"
        output_directory.mkdir(exist_ok=True)
        target_path, target_existed_before_save = build_outputs_readme_path(
            output_directory,
            root_path.name,
            readme_style,
            overwrite,
        )
        target_path.write_text(markdown_text, encoding="utf-8")

        if target_existed_before_save and overwrite:
            message = f"{target_path.name} in outputs was overwritten successfully."
            overwritten = True
        elif target_path.stem.endswith("_1") or re.search(r"_\d+$", target_path.stem):
            message = f"An output README already existed. Saved generated README as {target_path.name} instead."
            overwritten = False
        else:
            message = f"{target_path.name} created successfully in outputs."
            overwritten = False

        return {
            "saved_path": str(target_path),
            "filename": target_path.name,
            "overwritten": overwritten,
            "message": message,
        }

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
    readme_style: str = "detailed",
    save_location: str = "repo",
) -> dict:
    """Run the full README workflow and save the generated output."""
    root_path = validate_repo_path(repo_path)
    target_readme_path = root_path / "README.md"
    readme_existed_before_save = target_readme_path.exists()
    selected_style = normalize_readme_style(readme_style)

    scan_result = scan_repository(root_path)
    tech_stack = scan_result.get("tech_stack") or detect_tech_stack(root_path, scan_result=scan_result)
    run_info = scan_result.get("run_instructions") or detect_run_instructions(
        root_path,
        scan_result=scan_result,
        tech_stack=tech_stack,
    )

    from repo_health import analyze_repo_health

    health_report = analyze_repo_health(
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
        health_report=health_report,
        file_analysis=file_analysis,
        readme_style=selected_style,
    )

    save_result = save_readme(
        readme_preview,
        root_path,
        overwrite=overwrite,
        save_location=save_location,
        readme_style=selected_style,
    )

    if save_location == "repo" and save_result["filename"] == "README.md":
        save_result["overwritten"] = overwrite and readme_existed_before_save
        if save_result["overwritten"]:
            save_result["message"] = "README.md was overwritten."
        else:
            save_result["message"] = "README.md created successfully."

    return {
        "scan_result": scan_result,
        "tech_stack": tech_stack,
        "run_info": run_info,
        "health_report": health_report,
        "repo_health": health_report,
        "file_analysis": file_analysis,
        "readme_preview": readme_preview,
        "save_result": save_result,
        "readme_style": selected_style,
        "save_location": save_location,
    }


def main() -> int:
    """Simple CLI entry point for testing README generation manually."""
    parser = argparse.ArgumentParser(description="Generate README markdown for a local repository.")
    parser.add_argument("repo_path", help="Path to the target repository folder.")
    parser.add_argument(
        "--style",
        choices=["basic", "detailed", "beginner", "portfolio"],
        default="detailed",
        help="README style to generate.",
    )
    args = parser.parse_args()

    try:
        readme_text = generate_readme(args.repo_path, readme_style=args.style)
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
