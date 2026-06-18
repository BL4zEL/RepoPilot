from __future__ import annotations

from inspect import signature
from pathlib import Path

import streamlit as st

from file_understander import analyze_project_files
from readme_generator import save_readme, generate_readme
from repo_health import analyze_repo_health
from repo_scanner import scan_repository
from run_detector import detect_run_instructions
from tech_detector import detect_tech_stack


TECH_STACK_LABELS = [
    ("languages", "Languages"),
    ("frameworks", "Frameworks"),
    ("tools", "Tools"),
    ("databases", "Databases"),
    ("hardware", "Hardware"),
    ("package_managers", "Package Managers"),
]

README_STYLE_LABELS = {
    "detailed": "Detailed",
    "basic": "Basic",
    "beginner": "Beginner-Friendly",
    "portfolio": "Portfolio Showcase",
}

SAVE_LOCATION_LABELS = {
    "repo": "Save inside repo",
    "outputs": "Save to outputs folder",
}

STYLE_DOWNLOAD_FILE_NAMES = {
    "basic": "README_basic.md",
    "detailed": "README_detailed.md",
    "beginner": "README_beginner.md",
    "portfolio": "README_portfolio.md",
}


def inject_custom_css() -> None:
    """Inject a custom dark dashboard theme for the Streamlit app."""
    st.markdown(
        """
        <style>
        :root {
            --bg: #0b0f14;
            --panel: #111827;
            --panel-soft: #131922;
            --panel-alt: #0f1722;
            --border: rgba(255, 255, 255, 0.08);
            --text: #e5e7eb;
            --muted: #94a3b8;
            --accent: #3b82f6;
            --accent-soft: rgba(59, 130, 246, 0.14);
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
        }

        .stApp {
            background:
                radial-gradient(circle at top right, rgba(59, 130, 246, 0.10), transparent 24%),
                radial-gradient(circle at top left, rgba(34, 197, 94, 0.06), transparent 18%),
                linear-gradient(180deg, #0b0f14 0%, #0b1118 100%);
            color: var(--text);
        }

        .block-container {
            max-width: 1220px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        [data-testid="stHeader"] {
            background: rgba(11, 15, 20, 0.75);
            backdrop-filter: blur(10px);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0d131c 0%, #0b1118 100%);
            border-right: 1px solid var(--border);
        }

        [data-testid="stSidebar"] * {
            color: var(--text);
        }

        [data-testid="stMetric"] {
            background: linear-gradient(180deg, rgba(19, 25, 34, 0.96) 0%, rgba(17, 24, 39, 0.96) 100%);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 0.85rem 1rem;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.18);
        }

        [data-testid="stMetricLabel"] {
            color: var(--muted);
            font-size: 0.82rem;
        }

        [data-testid="stMetricValue"] {
            color: var(--text);
            font-size: 1.15rem;
        }

        .rp-section {
            margin-top: 1rem;
            margin-bottom: 1.1rem;
        }

        .rp-hero,
        .rp-card,
        .rp-subcard,
        .rp-tech-wrap,
        .rp-empty {
            background: linear-gradient(180deg, rgba(19, 25, 34, 0.96) 0%, rgba(17, 24, 39, 0.96) 100%);
            border: 1px solid var(--border);
            border-radius: 20px;
            box-shadow: 0 14px 30px rgba(0, 0, 0, 0.20);
        }

        .rp-hero {
            padding: 1.5rem 1.6rem 1.3rem 1.6rem;
            margin-bottom: 1rem;
        }

        .rp-card {
            padding: 1.1rem 1.2rem 1rem 1.2rem;
            margin-bottom: 1rem;
        }

        .rp-subcard {
            padding: 0.95rem 1rem;
            height: 100%;
        }

        .rp-eyebrow {
            color: #bfdbfe;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            margin-bottom: 0.55rem;
        }

        .rp-title {
            font-size: 2.35rem;
            line-height: 1.05;
            font-weight: 700;
            letter-spacing: -0.03em;
            margin: 0;
            color: var(--text);
        }

        .rp-subtitle {
            font-size: 1rem;
            line-height: 1.6;
            color: var(--muted);
            max-width: 780px;
            margin: 0.85rem 0 1rem 0;
        }

        .rp-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
        }

        .rp-badge {
            display: inline-flex;
            align-items: center;
            padding: 0.38rem 0.7rem;
            border-radius: 999px;
            border: 1px solid rgba(255, 255, 255, 0.09);
            background: rgba(255, 255, 255, 0.03);
            color: #dbeafe;
            font-size: 0.8rem;
        }

        .rp-mini-title {
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--text);
            margin-bottom: 0.35rem;
        }

        .rp-mini-copy,
        .rp-muted {
            color: var(--muted);
            font-size: 0.9rem;
            line-height: 1.55;
        }

        .rp-tech-wrap {
            padding: 1rem 1.1rem;
            margin-top: 0.75rem;
        }

        .rp-pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-top: 0.4rem;
        }

        .rp-pill {
            display: inline-flex;
            align-items: center;
            padding: 0.42rem 0.72rem;
            border-radius: 999px;
            background: rgba(59, 130, 246, 0.11);
            border: 1px solid rgba(59, 130, 246, 0.18);
            color: #dbeafe;
            font-size: 0.82rem;
            line-height: 1;
        }

        .rp-empty {
            padding: 1rem 1.1rem;
            color: var(--muted);
        }

        .rp-file-card {
            background: linear-gradient(180deg, rgba(15, 23, 34, 0.96) 0%, rgba(17, 24, 39, 0.96) 100%);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 0.95rem 1rem;
            margin-bottom: 0.8rem;
        }

        .rp-file-path {
            font-family: "Consolas", "SFMono-Regular", monospace;
            font-size: 0.86rem;
            color: #cbd5e1;
            margin-bottom: 0.4rem;
        }

        .rp-file-summary {
            color: var(--text);
            font-size: 0.9rem;
            line-height: 1.55;
        }

        .rp-kv {
            color: var(--muted);
            font-size: 0.82rem;
            margin-top: 0.55rem;
        }

        .rp-inline-code {
            font-family: "Consolas", "SFMono-Regular", monospace;
            color: #dbeafe;
        }

        .stTextInput > div > div,
        .stSelectbox > div > div,
        .stTextArea textarea {
            background: rgba(15, 23, 34, 0.95) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            border-radius: 14px !important;
        }

        .stTextInput label,
        .stSelectbox label,
        .stCheckbox label,
        .stRadio label,
        .stTextArea label {
            color: var(--text) !important;
        }

        .stButton > button,
        .stDownloadButton > button {
            border-radius: 14px !important;
            border: 1px solid rgba(59, 130, 246, 0.24) !important;
            background: linear-gradient(180deg, rgba(59, 130, 246, 0.95) 0%, rgba(37, 99, 235, 0.95) 100%) !important;
            color: white !important;
            font-weight: 600 !important;
            padding: 0.6rem 1rem !important;
            box-shadow: 0 10px 22px rgba(37, 99, 235, 0.18);
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            border-color: rgba(96, 165, 250, 0.45) !important;
            transform: translateY(-1px);
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
            background: rgba(17, 24, 39, 0.72);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 0.35rem;
        }

        .stTabs [data-baseweb="tab"] {
            height: 42px;
            background: transparent;
            border-radius: 12px;
            color: var(--muted);
            padding: 0 1rem;
        }

        .stTabs [aria-selected="true"] {
            background: rgba(59, 130, 246, 0.14) !important;
            color: #eaf2ff !important;
        }

        .stTabs [data-baseweb="tab-highlight"] {
            background: transparent !important;
        }

        .stCodeBlock,
        pre,
        code {
            border-radius: 16px !important;
        }

        [data-testid="stAlert"] {
            border-radius: 16px;
            border: 1px solid var(--border);
        }

        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, #3b82f6 0%, #22c55e 100%);
        }

        .rp-sidebar-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text);
            margin-bottom: 0.2rem;
        }

        .rp-sidebar-copy {
            color: var(--muted);
            font-size: 0.88rem;
            line-height: 1.55;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_session_state() -> None:
    """Create the session values used across Streamlit reruns."""
    default_values = {
        "repo_path": "",
        "readme_style": "detailed",
        "save_location": "repo",
        "save_location_choice": "repo",
        "last_rendered_style": None,
        "analyze_files": True,
        "use_ai": False,
        "save_overwrite": False,
        "save_overwrite_choice": False,
        "scan_result": None,
        "tech_stack": None,
        "run_info": None,
        "health_report": None,
        "repo_health": None,
        "file_analysis": None,
        "readme_markdown": "",
        "save_result": None,
        "last_error": "",
    }

    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value


def validate_repo_input(repo_path: str) -> tuple[bool, str]:
    """Validate the user-provided repo path before scanning."""
    if not repo_path.strip():
        return False, "Please enter a repo folder path."

    path = Path(repo_path).expanduser()
    if not path.exists():
        return False, "This path does not exist."
    if not path.is_dir():
        return False, "Please select a folder, not a file."
    return True, ""


def show_operation_error(message: str, error: Exception | str) -> None:
    """Show a friendly error and expose details in an expander."""
    st.session_state.last_error = str(error)
    st.error(message)
    with st.expander("Error details"):
        st.code(str(error), language="text")


def generate_readme_compatible(
    repo_path: str,
    scan_result: dict,
    tech_stack: dict,
    run_info: dict,
    health_report: dict,
    file_analysis: dict | None,
    readme_style: str,
) -> str:
    """Call generate_readme with backward-compatible keyword support."""
    parameters = signature(generate_readme).parameters
    kwargs = {
        "scan_result": scan_result,
        "tech_stack": tech_stack,
        "run_info": run_info,
        "file_analysis": file_analysis,
    }

    if "health_report" in parameters:
        kwargs["health_report"] = health_report
    elif "repo_health" in parameters:
        kwargs["repo_health"] = health_report

    if "readme_style" in parameters:
        kwargs["readme_style"] = readme_style

    return generate_readme(repo_path, **kwargs)


def save_readme_compatible(
    markdown_text: str,
    repo_path: str,
    overwrite: bool,
    save_location: str,
    readme_style: str,
) -> dict:
    """Call save_readme with backward-compatible keyword support."""
    parameters = signature(save_readme).parameters
    kwargs = {"overwrite": overwrite}

    if "save_location" in parameters:
        kwargs["save_location"] = save_location
    if "readme_style" in parameters:
        kwargs["readme_style"] = readme_style

    return save_readme(markdown_text, repo_path, **kwargs)


def render_sidebar() -> None:
    """Render the compact product sidebar."""
    with st.sidebar:
        st.markdown('<div class="rp-sidebar-title">RepoPilot Lite</div>', unsafe_allow_html=True)
        st.markdown('<div class="rp-sidebar-copy">Version: Lite</div>', unsafe_allow_html=True)
        st.divider()
        st.markdown("**Workflow**")
        st.markdown("1. Pick repo")
        st.markdown("2. Scan")
        st.markdown("3. Preview README")
        st.markdown("4. Save/export")
        st.divider()
        st.markdown("**Quick Tips**")
        st.markdown("- Use Portfolio style for GitHub showcase.")
        st.markdown("- Use Beginner style for student projects.")
        st.markdown("- Keep AI off for privacy and offline use.")


def render_hero_section() -> None:
    """Render the main product hero."""
    st.markdown(
        """
        <div class="rp-hero">
            <div class="rp-eyebrow">Developer README Toolkit</div>
            <h1 class="rp-title">RepoPilot Lite</h1>
            <p class="rp-subtitle">
                Turn messy project folders into clean GitHub-ready README files.
            </p>
            <div class="rp-badges">
                <span class="rp-badge">Offline-first</span>
                <span class="rp-badge">README Generator</span>
                <span class="rp-badge">Repo Health</span>
                <span class="rp-badge">File Understanding</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    feature_columns = st.columns(3)
    feature_cards = [
        ("Scan local repos", "Index project files, folders, structure, and important config safely on your machine."),
        ("Generate better READMEs", "Preview multiple README styles for documentation, beginner guidance, or portfolio polish."),
        ("Review project quality", "Surface tech stack, run commands, file logic, and health suggestions in one place."),
    ]
    for column, (title, copy) in zip(feature_columns, feature_cards):
        with column:
            st.markdown(
                f"""
                <div class="rp-subcard">
                    <div class="rp-mini-title">{title}</div>
                    <div class="rp-mini-copy">{copy}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_input_card() -> bool:
    """Render the main input controls and return whether scan was requested."""
    st.markdown('<div class="rp-card">', unsafe_allow_html=True)
    st.markdown("### Scan a Local Repository")
    st.markdown(
        '<div class="rp-muted">Paste the full path to the local project folder you want to scan.</div>',
        unsafe_allow_html=True,
    )

    st.text_input(
        "Enter local repo folder path",
        key="repo_path",
        placeholder=r"C:\Users\Akhil\Desktop\my-project",
    )

    control_columns = st.columns([1.2, 1, 1, 1])
    with control_columns[0]:
        st.selectbox(
            "README Style",
            options=["detailed", "basic", "beginner", "portfolio"],
            key="readme_style",
            format_func=lambda value: README_STYLE_LABELS[value],
        )
    with control_columns[1]:
        st.selectbox(
            "Save Location",
            options=["repo", "outputs"],
            key="save_location",
            format_func=lambda value: SAVE_LOCATION_LABELS[value],
        )
    with control_columns[2]:
        st.checkbox("Analyze important files", key="analyze_files")
    with control_columns[3]:
        st.checkbox("Use AI enhancement", key="use_ai")

    footer_columns = st.columns([1.35, 0.65])
    with footer_columns[0]:
        st.caption(
            "Basic = short and clean. Detailed = complete professional README. "
            "Beginner-Friendly = easy to understand. Portfolio Showcase = polished GitHub presentation."
        )
    with footer_columns[1]:
        st.checkbox("Overwrite existing README.md", key="save_overwrite")

    scan_clicked = st.button("Scan Repo", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    return scan_clicked


def scan_and_generate(repo_path: str, analyze_files: bool, use_ai: bool, readme_style: str) -> bool:
    """Run backend modules and store results in session state."""
    try:
        scan_result = scan_repository(
            repo_path,
            include_tech_stack=False,
            include_run_instructions=False,
        )
        tech_stack = detect_tech_stack(repo_path, scan_result=scan_result)
        run_info = detect_run_instructions(
            repo_path,
            scan_result=scan_result,
            tech_stack=tech_stack,
        )
        health_report = analyze_repo_health(
            repo_path,
            scan_result=scan_result,
            tech_stack=tech_stack,
            run_info=run_info,
        )
        file_analysis = None
        if analyze_files or use_ai:
            file_analysis = analyze_project_files(
                repo_path,
                scan_result=scan_result,
                tech_stack=tech_stack,
                use_ai=use_ai,
            )
        readme_markdown = generate_readme_compatible(
            repo_path,
            scan_result=scan_result,
            tech_stack=tech_stack,
            run_info=run_info,
            health_report=health_report,
            file_analysis=file_analysis,
            readme_style=readme_style,
        )
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError, ValueError) as error:
        show_operation_error("Something went wrong while scanning this repo.", error)
        return False
    except Exception as error:  # pragma: no cover - final guard for UI stability
        show_operation_error("Something went wrong while scanning this repo.", error)
        return False

    st.session_state.scan_result = scan_result
    st.session_state.tech_stack = tech_stack
    st.session_state.run_info = run_info
    st.session_state.health_report = health_report
    st.session_state.repo_health = health_report
    st.session_state.file_analysis = file_analysis
    st.session_state.readme_markdown = readme_markdown
    st.session_state.last_rendered_style = readme_style
    st.session_state.save_result = None
    st.session_state.last_error = ""
    return True


def regenerate_readme_preview(readme_style: str) -> None:
    """Regenerate the README preview without forcing a full rescan."""
    if not st.session_state.scan_result:
        return

    try:
        st.session_state.readme_markdown = generate_readme_compatible(
            st.session_state.repo_path,
            scan_result=st.session_state.scan_result,
            tech_stack=st.session_state.tech_stack,
            run_info=st.session_state.run_info,
            health_report=st.session_state.health_report or st.session_state.repo_health,
            file_analysis=st.session_state.file_analysis,
            readme_style=readme_style,
        )
        st.session_state.last_rendered_style = readme_style
        st.session_state.save_result = None
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError, ValueError) as error:
        show_operation_error("README preview could not be updated.", error)
    except Exception as error:  # pragma: no cover - final guard for UI stability
        show_operation_error("README preview could not be updated.", error)


def render_results_overview(scan_result: dict, health_report: dict) -> None:
    """Render the compact overview metrics."""
    metric_columns = st.columns(5)
    metric_columns[0].metric("Repo Name", scan_result["repo_name"])
    metric_columns[1].metric("Files", scan_result["total_files"])
    metric_columns[2].metric("Folders", scan_result["total_folders"])
    metric_columns[3].metric("Health Score", f"{health_report.get('score', 0)}/100")
    metric_columns[4].metric("Grade", health_report.get("grade", "N/A"))


def render_tech_stack_section(tech_stack: dict | None) -> None:
    """Show detected tech stack as compact pill badges."""
    st.markdown("### Detected Tech Stack")

    if not tech_stack:
        st.markdown('<div class="rp-empty">No major tech stack detected yet.</div>', unsafe_allow_html=True)
        return

    all_values: list[str] = []
    for key, _label in TECH_STACK_LABELS:
        all_values.extend(tech_stack.get(key, []))

    unique_values: list[str] = []
    for value in all_values:
        if value not in unique_values:
            unique_values.append(value)

    if not unique_values:
        st.markdown('<div class="rp-empty">No major tech stack detected yet.</div>', unsafe_allow_html=True)
        return

    pill_markup = "".join(f'<span class="rp-pill">{value}</span>' for value in unique_values)
    st.markdown(
        f"""
        <div class="rp-tech-wrap">
            <div class="rp-pill-row">{pill_markup}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_readme_tab(readme_markdown: str, readme_style: str) -> None:
    """Render the README preview tab."""
    st.markdown("### README Preview")
    st.markdown(readme_markdown)
    st.download_button(
        "Download README.md",
        data=readme_markdown,
        file_name=STYLE_DOWNLOAD_FILE_NAMES[readme_style],
        mime="text/markdown",
    )
    with st.expander("Raw Markdown"):
        st.code(readme_markdown, language="markdown")


def render_structure_tab(scan_result: dict) -> None:
    """Render project structure details."""
    info_columns = st.columns(3)
    info_columns[0].metric("Total Files", scan_result.get("total_files", 0))
    info_columns[1].metric("Total Folders", scan_result.get("total_folders", 0))
    info_columns[2].metric("Important Files", len(scan_result.get("important_files", [])))

    if scan_result.get("important_files"):
        preview_files = ", ".join(Path(path).name for path in scan_result["important_files"][:6])
        st.caption(f"Important files: {preview_files}")

    st.code(scan_result.get("project_tree", ""), language="text")


def render_run_tab(run_info: dict) -> None:
    """Render setup and run instructions."""
    st.markdown("### Setup Instructions")
    if run_info.get("setup_steps"):
        st.code("\n".join(run_info["setup_steps"]), language="bash")
    else:
        st.warning("No setup steps detected yet.")

    st.markdown("### How to Run")
    if run_info.get("run_commands"):
        st.code("\n".join(run_info["run_commands"]), language="bash")
    else:
        st.warning("No run command detected. Consider adding clear instructions to the README.")

    st.markdown("### Notes")
    if run_info.get("notes"):
        for note in run_info["notes"]:
            st.markdown(f"- {note}")
    else:
        st.markdown('<div class="rp-empty">No extra notes detected.</div>', unsafe_allow_html=True)


def render_health_tab(scan_result: dict, health_report: dict) -> None:
    """Render repository health details and suggestions."""
    st.markdown("### Repository Health")
    score = health_report.get("score", 0)
    grade = health_report.get("grade", "N/A")
    st.progress(score / 100 if score else 0)
    summary_columns = st.columns([1, 3])
    with summary_columns[0]:
        st.metric("Grade", grade)
    with summary_columns[1]:
        st.caption("Health score reflects README quality, entry points, tests, dependency files, and general repo readiness.")

    checks_table = []
    for check in health_report.get("checks", []):
        checks_table.append(
            {
                "Check": check["name"],
                "Status": "✅ Pass" if check["passed"] else "⚠️ Needs work",
                "Points": f"{check['points_awarded']}/{check['points_possible']}",
                "Message": check["message"],
            }
        )

    if checks_table:
        st.dataframe(checks_table, use_container_width=True, hide_index=True)

    detail_columns = st.columns(3)
    with detail_columns[0]:
        st.markdown("**Strengths**")
        if health_report.get("strengths"):
            for strength in health_report["strengths"]:
                st.markdown(f"- {strength}")
        else:
            st.markdown('<div class="rp-empty">No major strengths detected yet.</div>', unsafe_allow_html=True)
    with detail_columns[1]:
        st.markdown("**Issues**")
        if health_report.get("issues"):
            for issue in health_report["issues"]:
                st.markdown(f"- {issue}")
        else:
            st.markdown('<div class="rp-empty">No major issues detected.</div>', unsafe_allow_html=True)
    with detail_columns[2]:
        st.markdown("**Suggestions**")
        suggestions = health_report.get("suggestions") or build_suggestions(scan_result, health_report)
        if suggestions:
            for suggestion in suggestions:
                st.markdown(f"- {suggestion}")
        else:
            st.markdown('<div class="rp-empty">No suggestions right now.</div>', unsafe_allow_html=True)


def render_file_understanding_tab(file_analysis: dict | None, use_ai_requested: bool, analyze_files_requested: bool) -> None:
    """Render project logic and file-level summaries."""
    if not analyze_files_requested and not file_analysis:
        st.info('Enable "Analyze important files" and scan again to see file-level logic explanations.')
        return

    if not file_analysis:
        st.info("File analysis is not available for this scan.")
        return

    if use_ai_requested and any("OPENAI_API_KEY was not found" in item for item in file_analysis.get("limitations", [])):
        st.warning("AI mode was requested, but OPENAI_API_KEY was not found. RepoPilot used offline analysis instead.")

    st.markdown("### Project Logic Summary")
    st.markdown(
        f'<div class="rp-card"><div class="rp-mini-copy">{file_analysis.get("project_logic_summary", "Project logic summary is not available.")}</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown("### Analyzed Files")
    analyzed_files = file_analysis.get("analyzed_files", [])
    if not analyzed_files:
        st.markdown('<div class="rp-empty">No important files were analyzed.</div>', unsafe_allow_html=True)
    else:
        for file_info in analyzed_files:
            detected_patterns = ", ".join(file_info.get("detected_patterns", [])) or "None"
            names = file_info.get("important_functions", []) + file_info.get("important_classes", [])
            names_text = ", ".join(names[:10]) if names else "None"
            st.markdown(
                f"""
                <div class="rp-file-card">
                    <div class="rp-file-path">{file_info['path']}</div>
                    <div class="rp-file-summary">{file_info['summary']}</div>
                    <div class="rp-kv">Language: <span class="rp-inline-code">{file_info['language']}</span></div>
                    <div class="rp-kv">Detected patterns: {detected_patterns}</div>
                    <div class="rp-kv">Functions / classes: {names_text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if file_analysis.get("limitations"):
        with st.expander("Analysis notes"):
            for limitation in file_analysis["limitations"]:
                st.markdown(f"- {limitation}")


def build_suggestions(scan_result: dict, health_report: dict) -> list[str]:
    """Generate lightweight repo improvement suggestions."""
    if health_report.get("suggestions"):
        return health_report["suggestions"]

    files = {Path(file_path).name.lower() for file_path in scan_result.get("files", [])}
    suggestions: list[str] = []

    if not any("screenshot" in file_path.lower() for file_path in scan_result.get("files", [])):
        suggestions.append("Add screenshots")
    if not any("test" in file_path.lower() for file_path in scan_result.get("files", [])):
        suggestions.append("Add tests")
    suggestions.append("Add deployment instructions")
    if "license" not in files:
        suggestions.append("Add a license")
    if ".env.example" not in files:
        suggestions.append("Add .env.example for environment variables")
    return suggestions


def render_save_export_tab(repo_path: str, readme_markdown: str, readme_style: str) -> None:
    """Render save and export controls."""
    st.markdown("### Save and Export")
    st.caption(
        "If README.md already exists and overwrite is off, RepoPilot saves GENERATED_README.md instead."
    )

    if "save_location_choice" not in st.session_state:
        st.session_state.save_location_choice = st.session_state.save_location
    if "save_overwrite_choice" not in st.session_state:
        st.session_state.save_overwrite_choice = st.session_state.save_overwrite

    control_columns = st.columns(2)
    with control_columns[0]:
        st.selectbox(
            "Save Location",
            options=["repo", "outputs"],
            key="save_location_choice",
            format_func=lambda value: SAVE_LOCATION_LABELS[value],
        )
    with control_columns[1]:
        st.checkbox("Overwrite existing README.md", key="save_overwrite_choice")

    action_columns = st.columns(3)
    with action_columns[0]:
        if st.button("Save README", type="primary", use_container_width=True):
            try:
                save_result = save_readme_compatible(
                    readme_markdown,
                    repo_path,
                    overwrite=st.session_state.save_overwrite_choice,
                    save_location=st.session_state.save_location_choice,
                    readme_style=readme_style,
                )
                st.session_state.save_result = save_result
            except (FileNotFoundError, NotADirectoryError, PermissionError, OSError, ValueError) as error:
                show_operation_error("README could not be saved.", error)
            except Exception as error:  # pragma: no cover - final guard for UI stability
                show_operation_error("README could not be saved.", error)
    with action_columns[1]:
        st.download_button(
            "Download README.md",
            data=readme_markdown,
            file_name=STYLE_DOWNLOAD_FILE_NAMES[readme_style],
            mime="text/markdown",
            use_container_width=True,
        )
    with action_columns[2]:
        st.download_button(
            "Download GENERATED_README.md",
            data=readme_markdown,
            file_name="GENERATED_README.md",
            mime="text/markdown",
            use_container_width=True,
        )

    save_result = st.session_state.get("save_result")
    if save_result:
        if save_result["filename"] == "GENERATED_README.md":
            st.warning("README.md already existed, so RepoPilot saved GENERATED_README.md instead.")
        else:
            st.success(save_result["message"])
        st.code(save_result["saved_path"], language="text")

    with st.expander("Copyable Markdown"):
        st.code(readme_markdown, language="markdown")


def render_results(scan_result: dict, tech_stack: dict, run_info: dict, health_report: dict, file_analysis: dict | None) -> None:
    """Render the scan results dashboard."""
    render_results_overview(scan_result, health_report)
    render_tech_stack_section(tech_stack)

    tab_names = ["README", "Structure", "Run", "Health", "File Understanding", "Save / Export"]
    tabs = st.tabs(tab_names)

    with tabs[0]:
        render_readme_tab(st.session_state.readme_markdown, st.session_state.readme_style)
    with tabs[1]:
        render_structure_tab(scan_result)
    with tabs[2]:
        render_run_tab(run_info)
    with tabs[3]:
        render_health_tab(scan_result, health_report)
    with tabs[4]:
        render_file_understanding_tab(
            file_analysis,
            use_ai_requested=st.session_state.use_ai,
            analyze_files_requested=st.session_state.analyze_files,
        )
    with tabs[5]:
        render_save_export_tab(
            st.session_state.repo_path,
            st.session_state.readme_markdown,
            st.session_state.readme_style,
        )


def render_app() -> None:
    """Render the Streamlit app body."""
    st.set_page_config(
        page_title="RepoPilot Lite",
        page_icon="🚀",
        layout="wide",
    )

    inject_custom_css()
    initialize_session_state()
    render_sidebar()
    render_hero_section()

    scan_clicked = render_input_card()

    if scan_clicked:
        is_valid, message = validate_repo_input(st.session_state.repo_path)
        if not is_valid:
            if message == "Please enter a repo folder path.":
                st.warning(message)
            else:
                st.error(message)
        else:
            with st.spinner("Scanning repo and generating README..."):
                scan_succeeded = scan_and_generate(
                    st.session_state.repo_path,
                    analyze_files=st.session_state.analyze_files or st.session_state.use_ai,
                    use_ai=st.session_state.use_ai,
                    readme_style=st.session_state.readme_style,
                )
            if scan_succeeded:
                st.success("Repo scanned successfully.")

    if st.session_state.scan_result and st.session_state.last_rendered_style != st.session_state.readme_style:
        regenerate_readme_preview(st.session_state.readme_style)

    if not st.session_state.scan_result:
        st.markdown(
            """
            <div class="rp-empty">
                Run a scan to preview the README, inspect the project structure, review repo health,
                and export polished documentation.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Run locally with: `streamlit run streamlit_app.py`")
        return

    scan_result = st.session_state.scan_result
    tech_stack = st.session_state.tech_stack or {}
    run_info = st.session_state.run_info or {}
    health_report = st.session_state.health_report or st.session_state.repo_health or {}
    file_analysis = st.session_state.file_analysis

    render_results(scan_result, tech_stack, run_info, health_report, file_analysis)
    st.caption("Run locally with: `streamlit run streamlit_app.py`")


def main() -> None:
    """Run the Streamlit app with clean error handling."""
    try:
        render_app()
    except Exception as error:  # pragma: no cover - UI safety guard
        show_operation_error("RepoPilot Lite could not render correctly.", error)


if __name__ == "__main__":
    main()
