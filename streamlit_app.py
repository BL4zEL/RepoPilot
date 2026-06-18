from __future__ import annotations

from pathlib import Path

import streamlit as st

from readme_generator import generate_readme, save_readme
from repo_scanner import scan_repository
from run_detector import detect_run_instructions
from tech_detector import detect_tech_stack
from repo_health import analyze_repo_health


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
        "scan_result": None,
        "tech_stack": None,
        "run_info": None,
        "readme_markdown": "",
        "health_result": None,
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


def scan_and_generate(repo_path: str) -> None:
    """Run the existing backend modules and store results in session state."""
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
        readme_markdown = generate_readme(
            repo_path,
            scan_result=scan_result,
            tech_stack=tech_stack,
            run_info=run_info,
        )
        health_result = analyze_repo_health(
            repo_path,
            scan_result=scan_result,
            tech_stack=tech_stack,
            run_info=run_info,
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
    st.session_state.readme_markdown = readme_markdown
    st.session_state.health_result = health_result
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


def build_suggestions(scan_result: dict, tech_stack: dict) -> list[str]:
    """Generate lightweight README improvement suggestions."""
    files = {Path(file_path).name.lower() for file_path in scan_result.get("files", [])}
    suggestions: list[str] = []

    if not any("screenshot" in file_path.lower() for file_path in scan_result.get("files", [])):
        suggestions.append("Add screenshots")

    if not any("test" in file_path.lower() for file_path in scan_result.get("files", [])):
        suggestions.append("Add tests")

    suggestions.append("Add deployment instructions")

    if "license" not in files:
        suggestions.append("Add a license")

    if ".env.example" not in files and tech_stack.get("databases"):
        suggestions.append("Add .env.example for environment variables")
    elif ".env.example" not in files:
        suggestions.append("Add .env.example for environment variables")

    return suggestions


def render_suggestions_tab(scan_result: dict, tech_stack: dict) -> None:
    """Show simple future improvement ideas."""
    suggestions = build_suggestions(scan_result, tech_stack)
    for suggestion in suggestions:
        st.markdown(f"- {suggestion}")


def render_repo_health_tab(health_result: dict) -> None:
    """Render the Repo Health tab with score, checks, and suggestions."""
    if not health_result:
        st.info("Run a scan to see repo health analysis.")
        return

    # Score and grade already shown above, but we can show progress bar here
    score = health_result.get("score", 0)
    grade = health_result.get("grade", "N/A")

    st.markdown(f"**Score:** {score}/100 | **Grade:** {grade}")
    st.progress(score / 100)

    # Checks table
    st.subheader("Checks")
    checks = health_result.get("checks", [])
    if checks:
        check_data = []
        for check in checks:
            status = "✅ Pass" if check["passed"] else "❌ Fail"
            points = f"{check['points_awarded']}/{check['points_possible']}"
            check_data.append({
                "Check": check["name"],
                "Status": status,
                "Points": points,
                "Message": check["message"],
            })
        st.table(check_data)

    # Strengths section
    strengths = health_result.get("strengths", [])
    if strengths:
        st.subheader("Strengths")
        for strength in strengths:
            st.markdown(f"- {strength}")

    # Issues section
    issues = health_result.get("issues", [])
    if issues:
        st.subheader("Issues")
        for issue in issues:
            st.markdown(f"- {issue}")

    # Suggestions section
    suggestions = health_result.get("suggestions", [])
    if suggestions:
        st.subheader("Suggestions")
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
        page_icon="🌀",
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
        scan_clicked = st.form_submit_button("Scan Repo")

    if scan_clicked:
        is_valid, message = validate_repo_input(st.session_state.repo_path)
        if not is_valid:
            if message == "Please enter a repo folder path.":
                st.warning(message)
            else:
                st.error(message)
        else:
            scan_and_generate(st.session_state.repo_path)

    if not st.session_state.scan_result:
        st.info("Run a scan to preview the README, project structure, and setup instructions.")
        st.caption("Run locally with: `streamlit run streamlit_app.py`")
        return

    scan_result = st.session_state.scan_result
    tech_stack = st.session_state.tech_stack or {}
    run_info = st.session_state.run_info or {}
    readme_markdown = st.session_state.readme_markdown
    health_result = st.session_state.health_result or {}

    # Show repo health score metrics
    if health_result:
        health_cols = st.columns(2)
        health_cols[0].metric("Repo Health Score", f"{health_result.get('score', 0)}/100")
        health_cols[1].metric("Grade", health_result.get('grade', 'N/A'))

    metric_columns = st.columns(3)
    metric_columns[0].metric("Repo name", scan_result["repo_name"])
    metric_columns[1].metric("Total files", scan_result["total_files"])
    metric_columns[2].metric("Total folders", scan_result["total_folders"])

    render_tech_stack_section(tech_stack)

    preview_tab, structure_tab, run_tab, suggestions_tab, health_tab = st.tabs(
        ["README Preview", "Project Structure", "Setup & Run", "Suggestions", "Repo Health"]
    )

    with preview_tab:
        render_readme_preview_tab(readme_markdown)

    with structure_tab:
        render_project_structure_tab(scan_result)

    with run_tab:
        render_setup_and_run_tab(run_info)

    with suggestions_tab:
        render_suggestions_tab(scan_result, tech_stack)

    with health_tab:
        render_repo_health_tab(health_result)

    render_save_section(st.session_state.repo_path, readme_markdown)
    st.caption("Run locally with: `streamlit run streamlit_app.py`")


if __name__ == "__main__":
    main()
