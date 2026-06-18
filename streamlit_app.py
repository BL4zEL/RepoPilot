from __future__ import annotations

from pathlib import Path

import streamlit as st

from file_understander import analyze_project_files
from readme_generator import generate_readme, save_readme
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


def initialize_session_state() -> None:
    """Create the session values used across Streamlit reruns."""
    default_values = {
        "repo_path": "",
        "analyze_files": True,
        "use_ai": False,
        "scan_result": None,
        "tech_stack": None,
        "run_info": None,
        "repo_health": None,
        "file_analysis": None,
        "readme_markdown": "",
        "save_result": None,
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


def format_value_list(values: list[str]) -> str:
    """Format a list of values for display."""
    return ", ".join(values)


def scan_and_generate(repo_path: str, analyze_files: bool, use_ai: bool) -> None:
    """Run the backend modules and store results in session state."""
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
        repo_health = analyze_repo_health(
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
        readme_markdown = generate_readme(
            repo_path,
            scan_result=scan_result,
            tech_stack=tech_stack,
            run_info=run_info,
            repo_health=repo_health,
            file_analysis=file_analysis,
        )
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError, ValueError) as error:
        st.error(f"Scanning failed: {error}")
        return
    except Exception as error:  # pragma: no cover - final guard for UI stability
        st.error(f"Scanning failed: {error}")
        return

    st.session_state.scan_result = scan_result
    st.session_state.tech_stack = tech_stack
    st.session_state.run_info = run_info
    st.session_state.repo_health = repo_health
    st.session_state.file_analysis = file_analysis
    st.session_state.readme_markdown = readme_markdown
    st.session_state.save_result = None


def render_tech_stack_section(tech_stack: dict | None) -> None:
    """Show detected tech categories in a clean layout."""
    st.subheader("Detected Tech Stack")

    if not tech_stack:
        st.info("No major tech stack detected yet.")
        return

    visible_categories = [
        (label, tech_stack.get(key, []))
        for key, label in TECH_STACK_LABELS
        if tech_stack.get(key)
    ]

    if not visible_categories:
        st.info("No major tech stack detected yet.")
        return

    columns = st.columns(3)
    for index, (label, values) in enumerate(visible_categories):
        with columns[index % 3]:
            st.markdown(f"**{label}**")
            st.write(format_value_list(values))


def render_readme_preview_tab(readme_markdown: str) -> None:
    """Show rendered and raw README content."""
    st.markdown(readme_markdown)
    st.divider()
    st.markdown("**Raw Markdown**")
    st.code(readme_markdown, language="markdown")
    st.download_button(
        "Download README.md",
        data=readme_markdown,
        file_name="README.md",
        mime="text/markdown",
    )


def render_project_structure_tab(scan_result: dict) -> None:
    """Show the generated project tree."""
    st.code(scan_result.get("project_tree", ""), language="text")


def render_setup_and_run_tab(run_info: dict) -> None:
    """Show setup steps, run commands, and notes."""
    st.markdown("**Setup Steps**")
    if run_info.get("setup_steps"):
        st.code("\n".join(run_info["setup_steps"]), language="bash")
    else:
        st.info("No setup steps detected.")

    st.markdown("**Run Commands**")
    if run_info.get("run_commands"):
        st.code("\n".join(run_info["run_commands"]), language="bash")
    else:
        st.info("No run commands detected.")

    st.markdown("**Notes**")
    if run_info.get("notes"):
        for note in run_info["notes"]:
            st.markdown(f"- {note}")
    else:
        st.info("No extra notes detected.")


def render_repo_health_tab(repo_health: dict) -> None:
    """Show the repo health score, checks, and follow-up ideas."""
    st.subheader(f"Score: {repo_health['score']}/100")
    st.write(f"Grade: **{repo_health['grade']}**")
    st.progress(repo_health["score"] / 100)

    checks_table = [
        {
            "Check": check["name"],
            "Status": "Passed" if check["passed"] else "Needs work",
            "Points": f"{check['points_awarded']}/{check['points_possible']}",
            "Message": check["message"],
        }
        for check in repo_health.get("checks", [])
    ]
    st.dataframe(checks_table, use_container_width=True, hide_index=True)

    st.markdown("**Strengths**")
    if repo_health.get("strengths"):
        for strength in repo_health["strengths"]:
            st.markdown(f"- {strength}")
    else:
        st.info("No major strengths detected yet.")

    st.markdown("**Issues**")
    if repo_health.get("issues"):
        for issue in repo_health["issues"]:
            st.markdown(f"- {issue}")
    else:
        st.info("No major issues detected.")

    st.markdown("**Suggestions**")
    if repo_health.get("suggestions"):
        for suggestion in repo_health["suggestions"]:
            st.markdown(f"- {suggestion}")
    else:
        st.info("No suggestions right now.")


def render_file_understanding_tab(file_analysis: dict | None, use_ai_requested: bool) -> None:
    """Show the project logic summary and per-file analysis."""
    if not file_analysis:
        st.info("File analysis is not available for this scan.")
        return

    if use_ai_requested and any("OPENAI_API_KEY was not found" in item for item in file_analysis.get("limitations", [])):
        st.warning("AI mode was requested, but OPENAI_API_KEY was not found. RepoPilot used offline analysis instead.")

    st.markdown("**Project Logic Summary**")
    st.write(file_analysis.get("project_logic_summary", "Project logic summary is not available."))

    table_rows = []
    for file_info in file_analysis.get("analyzed_files", []):
        names = file_info.get("important_functions", []) + file_info.get("important_classes", [])
        table_rows.append(
            {
                "File": file_info["path"],
                "Language": file_info["language"],
                "Summary": file_info["summary"],
                "Detected patterns": ", ".join(file_info.get("detected_patterns", [])),
                "Functions / classes": ", ".join(names[:10]),
            }
        )

    if table_rows:
        st.dataframe(table_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No important files were analyzed.")

    st.markdown("**Limitations**")
    if file_analysis.get("limitations"):
        for limitation in file_analysis["limitations"]:
            st.markdown(f"- {limitation}")
    else:
        st.info("No limitations reported.")


def build_suggestions(scan_result: dict, tech_stack: dict, repo_health: dict) -> list[str]:
    """Generate lightweight README improvement suggestions."""
    if repo_health.get("suggestions"):
        return repo_health["suggestions"]

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


def render_suggestions_tab(scan_result: dict, tech_stack: dict, repo_health: dict) -> None:
    """Show simple future improvement ideas."""
    suggestions = build_suggestions(scan_result, tech_stack, repo_health)
    for suggestion in suggestions:
        st.markdown(f"- {suggestion}")


def render_save_section(repo_path: str, readme_markdown: str) -> None:
    """Render save controls and save result messages."""
    st.subheader("Save README")
    overwrite = st.checkbox("Overwrite existing README.md", value=False)

    if st.button("Save README to Repo", type="primary"):
        try:
            save_result = save_readme(readme_markdown, repo_path, overwrite=overwrite)
            st.session_state.save_result = save_result
        except (FileNotFoundError, NotADirectoryError, PermissionError, OSError, ValueError) as error:
            st.error(f"Saving failed: {error}")
        except Exception as error:  # pragma: no cover - final guard for UI stability
            st.error(f"Saving failed: {error}")

    save_result = st.session_state.get("save_result")
    if not save_result:
        return

    saved_path = save_result["saved_path"]
    if save_result["filename"] == "GENERATED_README.md":
        st.warning("README.md already existed, so RepoPilot saved GENERATED_README.md instead.")
        st.info(f"Saved file path: {saved_path}")
    else:
        st.success(f"README saved successfully at: {saved_path}")


def main() -> None:
    """Render the Streamlit app."""
    st.set_page_config(
        page_title="RepoPilot Lite",
        page_icon="🚀",
        layout="wide",
    )

    initialize_session_state()

    st.title("RepoPilot Lite")
    st.caption("Turn messy project folders into clean GitHub-ready README files.")
    st.write(
        "Select a local repo folder, scan it, preview the generated README, then save or download it."
    )

    with st.form("scan_form"):
        st.text_input(
            "Enter local repo folder path",
            key="repo_path",
            placeholder=r"C:\Users\Akhil\Desktop\my-project",
        )
        st.checkbox("Analyze important files for deeper explanation", key="analyze_files", value=True)
        st.checkbox("Use AI for better explanation", key="use_ai", value=False)
        scan_clicked = st.form_submit_button("Scan Repo")

    if scan_clicked:
        is_valid, message = validate_repo_input(st.session_state.repo_path)
        if not is_valid:
            if message == "Please enter a repo folder path.":
                st.warning(message)
            else:
                st.error(message)
        else:
            scan_and_generate(
                st.session_state.repo_path,
                analyze_files=st.session_state.analyze_files or st.session_state.use_ai,
                use_ai=st.session_state.use_ai,
            )

    if not st.session_state.scan_result:
        st.info("Run a scan to preview the README, project structure, and setup instructions.")
        st.caption("Run locally with: `streamlit run streamlit_app.py`")
        return

    scan_result = st.session_state.scan_result
    tech_stack = st.session_state.tech_stack or {}
    run_info = st.session_state.run_info or {}
    repo_health = st.session_state.repo_health or {}
    file_analysis = st.session_state.file_analysis
    readme_markdown = st.session_state.readme_markdown

    metric_columns = st.columns(5)
    metric_columns[0].metric("Repo name", scan_result["repo_name"])
    metric_columns[1].metric("Total files", scan_result["total_files"])
    metric_columns[2].metric("Total folders", scan_result["total_folders"])
    metric_columns[3].metric("Repo Health Score", f"{repo_health.get('score', 0)}/100")
    metric_columns[4].metric("Grade", repo_health.get("grade", "N/A"))

    render_tech_stack_section(tech_stack)

    tab_names = ["README Preview", "Project Structure", "Setup & Run", "Suggestions", "Repo Health"]
    if st.session_state.analyze_files or st.session_state.use_ai:
        tab_names.append("File Understanding")

    tabs = st.tabs(tab_names)
    tab_map = dict(zip(tab_names, tabs))

    with tab_map["README Preview"]:
        render_readme_preview_tab(readme_markdown)

    with tab_map["Project Structure"]:
        render_project_structure_tab(scan_result)

    with tab_map["Setup & Run"]:
        render_setup_and_run_tab(run_info)

    with tab_map["Suggestions"]:
        render_suggestions_tab(scan_result, tech_stack, repo_health)

    with tab_map["Repo Health"]:
        render_repo_health_tab(repo_health)

    if "File Understanding" in tab_map:
        with tab_map["File Understanding"]:
            render_file_understanding_tab(file_analysis, st.session_state.use_ai)

    render_save_section(st.session_state.repo_path, readme_markdown)
    st.caption("Run locally with: `streamlit run streamlit_app.py`")


if __name__ == "__main__":
    main()
