from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path

from repo_scanner import scan_repository, validate_repo_path
from tech_detector import detect_tech_stack


DEFAULT_MAX_FILES = 12
DEFAULT_MAX_CHARS_PER_FILE = 8000
DEFAULT_MAX_TOTAL_CHARS = 40000
MAX_FILE_SIZE_BYTES = 250 * 1024

ALLOWED_SOURCE_SUFFIXES = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".ino",
    ".cpp",
    ".c",
    ".java",
}

NON_TEXT_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".webp",
    ".svg",
    ".mp4",
    ".mov",
    ".avi",
    ".mp3",
    ".wav",
    ".ogg",
    ".csv",
    ".xlsx",
    ".xls",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".pkl",
    ".pt",
    ".onnx",
    ".exe",
    ".dll",
    ".zip",
    ".rar",
    ".7z",
    ".bin",
    ".pdf",
}

ALLOWED_CONFIG_NAMES = {
    "package.json",
    "requirements.txt",
    "dockerfile",
    "platformio.ini",
}

PRIORITY_PATHS = [
    "app.py",
    "main.py",
    "streamlit_app.py",
    "manage.py",
    "server.js",
    "index.js",
    "src/app.jsx",
    "src/main.jsx",
    "src/app.tsx",
    "src/main.tsx",
    "player_analyzer.py",
    "routes.py",
    "views.py",
    "models.py",
    "templates/index.html",
    "static/script.js",
    "static/style.css",
    "package.json",
    "requirements.txt",
    "dockerfile",
    "platformio.ini",
]

PRIORITY_PREFIXES = [
    "controllers/",
    "services/",
    "utils/",
]

SECRET_MARKERS = [
    "API_KEY",
    "SECRET",
    "PASSWORD",
    "TOKEN",
    "PRIVATE_KEY",
    "MONGO_URI",
    "DATABASE_URL",
    "OPENAI_API_KEY",
]

LANGUAGE_NAMES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript / React JSX",
    ".ts": "TypeScript",
    ".tsx": "TypeScript / React TSX",
    ".html": "HTML",
    ".css": "CSS",
    ".ino": "Arduino",
    ".cpp": "C++",
    ".c": "C",
    ".java": "Java",
}


def safe_read_text(file_path: Path, max_chars: int) -> str:
    """Read a limited amount of text while ignoring encoding problems."""
    try:
        with file_path.open("r", encoding="utf-8", errors="ignore") as file_handle:
            return file_handle.read(max_chars).lstrip("\ufeff")
    except OSError:
        return ""


def should_consider_file(relative_path: str) -> bool:
    """Decide whether a file is safe and relevant for analysis."""
    path = Path(relative_path)
    suffix = path.suffix.lower()
    file_name = path.name.lower()

    if suffix in NON_TEXT_SUFFIXES:
        return False

    if suffix in ALLOWED_SOURCE_SUFFIXES:
        return True

    return file_name in ALLOWED_CONFIG_NAMES


def detect_language(file_path: str) -> str:
    """Convert a file path into a user-friendly language name."""
    path = Path(file_path)
    if path.name.lower() == "dockerfile":
        return "Docker"
    if path.name.lower() == "requirements.txt":
        return "Requirements"
    if path.name.lower() == "package.json":
        return "JSON / Node config"
    if path.name.lower() == "platformio.ini":
        return "PlatformIO config"
    return LANGUAGE_NAMES.get(path.suffix.lower(), "Text")


def select_files_for_analysis(scan_result: dict, max_files: int) -> list[str]:
    """Choose the most important files to analyze first."""
    files = [path for path in scan_result.get("files", []) if should_consider_file(path)]
    files_lower_map = {path.lower(): path for path in files}

    selected: list[str] = []

    for priority_path in PRIORITY_PATHS:
        actual_path = files_lower_map.get(priority_path)
        if actual_path and actual_path not in selected:
            selected.append(actual_path)

    for file_path in sorted(files, key=str.lower):
        file_lower = file_path.lower()
        if any(file_lower.startswith(prefix) for prefix in PRIORITY_PREFIXES) and file_path not in selected:
            selected.append(file_path)

    for file_path in sorted(files, key=lambda path: (Path(path).suffix.lower(), path.lower())):
        if file_path not in selected:
            selected.append(file_path)

    return selected[:max_files]


def extract_python_symbols(text: str) -> tuple[list[str], list[str]]:
    """Extract top-level function and class names from Python code."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [], []

    functions = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    classes = [
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    ]
    return functions[:12], classes[:12]


def extract_js_functions(text: str) -> list[str]:
    """Extract likely function names from JavaScript or TypeScript."""
    patterns = [
        r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        r"\bconst\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\(",
        r"\blet\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\(",
        r"\bvar\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\(",
    ]

    found: list[str] = []
    for pattern in patterns:
        for match in re.findall(pattern, text):
            if match not in found:
                found.append(match)

    return found[:12]


def summarize_python_file(text: str) -> tuple[str, list[str], list[str], list[str]]:
    """Create an offline summary for a Python file."""
    lower_text = text.lower()
    functions, classes = extract_python_symbols(text)
    patterns: list[str] = []

    if "from flask import flask" in lower_text or "@app.route" in lower_text or "render_template" in lower_text:
        patterns.append("Flask routes")
    if "jsonify" in lower_text:
        patterns.append("JSON API")
    if "render_template" in lower_text:
        patterns.append("Template rendering")
    if "import streamlit" in lower_text or "st." in lower_text:
        patterns.append("Streamlit UI")
    if "from fastapi import fastapi" in lower_text or "@app.get" in lower_text or "@app.post" in lower_text:
        patterns.append("FastAPI endpoints")
    if "models.model" in lower_text or "urlpatterns" in lower_text:
        patterns.append("Django app logic")
    if "cv2" in lower_text:
        patterns.append("OpenCV processing")
    if "ultralytics" in lower_text or "yolo" in lower_text:
        patterns.append("YOLO inference")
    if "pymongo" in lower_text or "mongoclient" in lower_text:
        patterns.append("MongoDB access")
    if "firebase_admin" in lower_text:
        patterns.append("Firebase admin")
    if classes:
        patterns.append("Classes")
    if functions and not patterns:
        patterns.append("Helper functions")

    if "Flask routes" in patterns:
        summary = "This file defines the Flask backend, including routes, request handling, and responses for the web app."
    elif "Streamlit UI" in patterns:
        summary = "This file builds the Streamlit interface and connects user inputs to backend project analysis functions."
    elif "FastAPI endpoints" in patterns:
        summary = "This file defines FastAPI endpoints and handles request and response flow for the application."
    elif "Django app logic" in patterns:
        summary = "This file is part of the Django application structure and appears to define routing, models, or view logic."
    elif "OpenCV processing" in patterns or "YOLO inference" in patterns:
        summary = "This file handles computer vision or model inference logic used by the project."
    elif functions or classes:
        summary = "This file contains helper functions or classes used by other parts of the project."
    else:
        summary = "This file contains Python logic that supports the project."

    return summary, functions, classes, patterns


def summarize_javascript_file(text: str) -> tuple[str, list[str], list[str], list[str]]:
    """Create an offline summary for JavaScript or TypeScript."""
    lower_text = text.lower()
    functions = extract_js_functions(text)
    patterns: list[str] = []

    if "import react" in lower_text or "usestate" in lower_text or "useeffect" in lower_text or "return (" in text:
        patterns.append("React components")
    if "express()" in lower_text or "app.get(" in lower_text or "app.post(" in lower_text:
        patterns.append("Express routes")
    if "document.queryselector" in lower_text or "addeventlistener" in lower_text:
        patterns.append("DOM events")
    if "fetch(" in lower_text or "axios" in lower_text:
        patterns.append("API calls")

    if "React components" in patterns:
        summary = "This file builds interactive frontend behavior, likely through React components and UI state handling."
    elif "Express routes" in patterns:
        summary = "This file defines backend server logic and route handlers for the JavaScript application."
    elif "DOM events" in patterns:
        summary = "This file controls browser-side behavior, including DOM updates and event handling."
    elif "API calls" in patterns:
        summary = "This file connects the frontend or backend to external or internal APIs."
    else:
        summary = "This file contains JavaScript or TypeScript logic used by the project."

    return summary, functions, [], patterns


def summarize_html_file(text: str) -> tuple[str, list[str], list[str], list[str]]:
    """Create an offline summary for HTML."""
    lower_text = text.lower()
    patterns: list[str] = []

    if "<form" in lower_text:
        patterns.append("Forms")
    if "<script" in lower_text:
        patterns.append("Scripts")
    if "stylesheet" in lower_text or "<link" in lower_text:
        patterns.append("Stylesheets")
    if any(tag in lower_text for tag in ["<main", "<section", "<header", "<footer"]):
        patterns.append("UI sections")

    summary = "This file defines the main HTML structure of the user interface, including page sections, linked assets, and interactive elements."
    return summary, [], [], patterns


def summarize_css_file(text: str) -> tuple[str, list[str], list[str], list[str]]:
    """Create an offline summary for CSS."""
    lower_text = text.lower()
    patterns: list[str] = []

    if "display: flex" in lower_text or "display:flex" in lower_text or "display: grid" in lower_text or "display:grid" in lower_text:
        patterns.append("Layout styling")
    if "@media" in lower_text:
        patterns.append("Responsive rules")
    if "dark" in lower_text or "light" in lower_text or "color-scheme" in lower_text:
        patterns.append("Theme styling")
    if "@keyframes" in lower_text or "animation:" in lower_text:
        patterns.append("Animations")

    summary = "This file styles the user interface and controls layout, colors, spacing, and presentation details."
    return summary, [], [], patterns


def summarize_requirements_file(text: str) -> tuple[str, list[str], list[str], list[str]]:
    """Create a summary for requirements.txt."""
    dependencies = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    preview = ", ".join(dependencies[:5]) if dependencies else "no clear dependencies"
    summary = f"This file lists Python dependencies needed to run the project, including {preview}."
    return summary, [], [], ["Python dependencies"]


def summarize_package_json(text: str) -> tuple[str, list[str], list[str], list[str]]:
    """Create a summary for package.json."""
    try:
        package_data = json.loads(text)
    except json.JSONDecodeError:
        package_data = {}

    scripts = package_data.get("scripts", {})
    dependencies = package_data.get("dependencies", {})
    dev_dependencies = package_data.get("devDependencies", {})
    patterns = ["npm scripts"]

    if any(name in dependencies for name in ["react", "next", "vue", "angular"]):
        patterns.append("Frontend dependencies")
    if "express" in dependencies:
        patterns.append("Backend dependencies")

    script_names = ", ".join(list(scripts)[:4]) if isinstance(scripts, dict) and scripts else "no clear scripts"
    dependency_count = 0
    if isinstance(dependencies, dict):
        dependency_count += len(dependencies)
    if isinstance(dev_dependencies, dict):
        dependency_count += len(dev_dependencies)

    summary = (
        f"This file configures the Node.js project, including npm scripts such as {script_names} "
        f"and around {dependency_count} dependencies."
    )
    return summary, [], [], patterns


def summarize_dockerfile(text: str) -> tuple[str, list[str], list[str], list[str]]:
    """Create a summary for Dockerfile."""
    lower_text = text.lower()
    patterns = ["Container setup"]
    if "expose" in lower_text:
        patterns.append("Port exposure")
    if "cmd" in lower_text or "entrypoint" in lower_text:
        patterns.append("Startup command")

    summary = "This file describes how to build and run the project inside a Docker container."
    return summary, [], [], patterns


def summarize_platformio(text: str) -> tuple[str, list[str], list[str], list[str]]:
    """Create a summary for platformio.ini."""
    board_match = re.search(r"^\s*board\s*=\s*(.+)$", text, flags=re.MULTILINE)
    framework_match = re.search(r"^\s*framework\s*=\s*(.+)$", text, flags=re.MULTILINE)
    board_text = board_match.group(1).strip() if board_match else "an embedded board"
    framework_text = framework_match.group(1).strip() if framework_match else "its configured framework"
    summary = f"This file configures PlatformIO for {board_text} and defines build settings for {framework_text}."
    return summary, [], [], ["PlatformIO config"]


def summarize_arduino_like_file(text: str) -> tuple[str, list[str], list[str], list[str]]:
    """Create a summary for Arduino or embedded code."""
    lower_text = text.lower()
    patterns: list[str] = []

    if "setup(" in lower_text:
        patterns.append("setup()")
    if "loop(" in lower_text:
        patterns.append("loop()")
    if "wifi" in lower_text:
        patterns.append("WiFi")
    if "webserver" in lower_text:
        patterns.append("WebServer")
    if "digitalwrite" in lower_text:
        patterns.append("GPIO output")
    if "relay" in lower_text:
        patterns.append("Relay control")
    if any(word in lower_text for word in ["sensor", "temperature", "humidity", "ultrasonic"]):
        patterns.append("Sensor logic")

    summary = "This file contains embedded firmware logic that initializes hardware and handles repeated device behavior."
    return summary, [], [], patterns


def summarize_generic_text_file(language: str) -> tuple[str, list[str], list[str], list[str]]:
    """Fallback summary for supported file types."""
    return f"This file contains {language.lower()} logic used by the project.", [], [], []


def summarize_file_by_type(relative_path: str, text: str) -> tuple[str, list[str], list[str], list[str]]:
    """Route a file to the right heuristic summarizer."""
    path = Path(relative_path)
    file_name = path.name.lower()
    suffix = path.suffix.lower()
    language = detect_language(relative_path)

    if suffix == ".py":
        return summarize_python_file(text)
    if suffix in {".js", ".jsx", ".ts", ".tsx"}:
        return summarize_javascript_file(text)
    if suffix == ".html":
        return summarize_html_file(text)
    if suffix == ".css":
        return summarize_css_file(text)
    if file_name == "requirements.txt":
        return summarize_requirements_file(text)
    if file_name == "package.json":
        return summarize_package_json(text)
    if file_name == "dockerfile":
        return summarize_dockerfile(text)
    if file_name == "platformio.ini":
        return summarize_platformio(text)
    if suffix in {".ino", ".cpp", ".c", ".java"}:
        return summarize_arduino_like_file(text)

    return summarize_generic_text_file(language)


def summarize_project_logic(tech_stack: dict, analyzed_files: list[dict]) -> str:
    """Build a beginner-friendly explanation of how the project fits together."""
    analyzed_paths = {file_info["path"].lower() for file_info in analyzed_files}
    frameworks = set(tech_stack.get("frameworks", []))
    languages = set(tech_stack.get("languages", []))

    if "Flask" in frameworks:
        return (
            "The project follows a simple Flask architecture. app.py likely starts the backend server, "
            "handles routes, and connects templates or API responses to the rest of the project. "
            "Supporting files provide frontend assets, helper logic, or configuration."
        )

    if "Streamlit" in frameworks or "streamlit_app.py" in analyzed_paths:
        return (
            "The project is organized around a Streamlit interface. streamlit_app.py collects user input, "
            "shows results, and connects the UI to backend helper modules that perform the main analysis or processing work."
        )

    if "React" in frameworks or any(path in analyzed_paths for path in {"src/app.jsx", "src/main.jsx", "src/app.tsx", "src/main.tsx"}):
        return (
            "The project uses a frontend component structure. Entry files mount the application, while component and utility files "
            "handle the main interface flow and supporting browser logic."
        )

    if "Arduino" in languages or any(path.endswith(".ino") for path in analyzed_paths):
        return (
            "The project is centered around firmware logic. The main embedded file initializes hardware in setup() "
            "and then repeatedly handles sensors, connectivity, or device control inside loop()."
        )

    if analyzed_files:
        file_names = ", ".join(file_info["path"] for file_info in analyzed_files[:3])
        return (
            f"The project is organized across a few key files, including {file_names}. "
            "These files define the main entry points, supporting logic, and configuration needed to run the application."
        )

    return "The project contains source files and configuration that work together to run the application."


def sanitize_text_for_ai(text: str) -> str:
    """Remove obvious secret-looking lines before any optional AI request."""
    safe_lines: list[str] = []
    for line in text.splitlines():
        upper_line = line.upper()
        if any(marker in upper_line for marker in SECRET_MARKERS):
            safe_lines.append("[REDACTED SECRET-LIKE LINE]")
        else:
            safe_lines.append(line)
    return "\n".join(safe_lines)


def prepare_ai_payload(analyzed_files: list[dict]) -> list[dict]:
    """Prepare a reduced payload for optional AI improvement."""
    payload: list[dict] = []
    for file_info in analyzed_files:
        payload.append(
            {
                "path": file_info["path"],
                "language": file_info["language"],
                "summary": file_info["summary"],
                "important_functions": file_info["important_functions"],
                "important_classes": file_info.get("important_classes", []),
                "detected_patterns": file_info["detected_patterns"],
                "snippet": sanitize_text_for_ai(file_info.get("snippet", ""))[:1200],
            }
        )
    return payload


def strip_code_fences(text: str) -> str:
    """Remove simple markdown code fences from AI JSON output."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def improve_with_ai(analyzed_files: list[dict], project_logic_summary: str) -> tuple[list[dict], str, list[str]]:
    """
    Optionally improve summaries with AI.

    This is strictly best-effort. Any failure falls back to heuristic output.
    """
    limitations: list[str] = []
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        limitations.append("AI mode requested but OPENAI_API_KEY was not found.")
        return analyzed_files, project_logic_summary, limitations

    try:
        from openai import OpenAI
    except ImportError:
        limitations.append("AI mode requested but the OpenAI package is not installed.")
        return analyzed_files, project_logic_summary, limitations

    prompt_payload = prepare_ai_payload(analyzed_files)
    prompt = (
        "You are improving beginner-friendly code summaries for a local repo analysis tool.\n"
        "Return JSON with keys: analyzed_files, project_logic_summary.\n"
        "Each analyzed_files item must include: path, summary, detected_patterns, important_functions, important_classes.\n"
        "Keep summaries short, accurate, and beginner-friendly. Do not mention secrets.\n"
        f"Current project logic summary: {project_logic_summary}\n"
        f"File payload: {json.dumps(prompt_payload)}"
    )

    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            input=prompt,
        )
        response_text = strip_code_fences(response.output_text)
        response_data = json.loads(response_text)
    except Exception as error:  # pragma: no cover - depends on optional API setup
        limitations.append(f"AI enhancement failed, so heuristic summaries were used instead: {error}")
        return analyzed_files, project_logic_summary, limitations

    improved_files_map = {
        item.get("path"): item
        for item in response_data.get("analyzed_files", [])
        if isinstance(item, dict) and item.get("path")
    }

    improved_files: list[dict] = []
    for file_info in analyzed_files:
        improved = improved_files_map.get(file_info["path"])
        if not improved:
            improved_files.append(file_info)
            continue

        improved_files.append(
            {
                **file_info,
                "summary": improved.get("summary", file_info["summary"]),
                "important_functions": improved.get("important_functions", file_info["important_functions"]),
                "important_classes": improved.get("important_classes", file_info.get("important_classes", [])),
                "detected_patterns": improved.get("detected_patterns", file_info["detected_patterns"]),
            }
        )

    improved_project_logic = response_data.get("project_logic_summary", project_logic_summary)
    return improved_files, improved_project_logic, limitations


def analyze_project_files(
    repo_path,
    scan_result=None,
    tech_stack=None,
    use_ai=False,
    max_files=12,
    max_chars_per_file=8000,
    max_total_chars=40000,
):
    """
    Analyze important project files and explain how the codebase works.

    The default mode is fully offline and heuristic-based. AI is optional and
    only used when the caller explicitly enables it.
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

    selected_files = select_files_for_analysis(scan_result, max_files=max_files)

    analyzed_files: list[dict] = []
    limitations: list[str] = []
    total_chars_read = 0
    skipped_large_file = False

    for relative_path in selected_files:
        absolute_path = root_path / Path(relative_path)
        file_name = absolute_path.name.lower()

        if not absolute_path.exists() or not absolute_path.is_file():
            continue

        try:
            file_size = absolute_path.stat().st_size
        except OSError:
            continue

        if file_size > MAX_FILE_SIZE_BYTES and file_name not in {"package.json", "requirements.txt"}:
            skipped_large_file = True
            continue

        remaining_chars = max_total_chars - total_chars_read
        if remaining_chars <= 0:
            limitations.append("Total analysis size limit was reached, so some files were skipped.")
            break

        chars_to_read = min(max_chars_per_file, remaining_chars)
        text = safe_read_text(absolute_path, chars_to_read)
        if not text.strip():
            continue

        summary, functions, classes, patterns = summarize_file_by_type(relative_path, text)
        analyzed_files.append(
            {
                "path": relative_path,
                "language": detect_language(relative_path),
                "size_chars": len(text),
                "summary": summary,
                "important_functions": functions,
                "important_classes": classes,
                "detected_patterns": patterns,
                # Keep a temporary snippet for optional AI refinement only.
                "snippet": text,
            }
        )
        total_chars_read += len(text)

    if skipped_large_file:
        limitations.append("Large files were skipped.")

    if not use_ai:
        limitations.append("AI mode was disabled, so summaries are heuristic-based.")

    project_logic_summary = summarize_project_logic(tech_stack, analyzed_files)

    if use_ai:
        analyzed_files, project_logic_summary, ai_limitations = improve_with_ai(
            analyzed_files,
            project_logic_summary,
        )
        for limitation in ai_limitations:
            if limitation not in limitations:
                limitations.append(limitation)

    for file_info in analyzed_files:
        file_info.pop("snippet", None)

    return {
        "analyzed_files": analyzed_files,
        "project_logic_summary": project_logic_summary,
        "limitations": limitations,
    }
