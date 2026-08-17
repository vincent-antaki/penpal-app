import streamlit as st
import os
import glob
import json
import subprocess
import sys
import argparse
import base64

try:
    import cairosvg
except ImportError:
    cairosvg = None


# Default locations
default_workspace = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
default_gallery = os.environ.get(
    "PENPAL_GALLERY_DIR", os.path.join(default_workspace, "gallery")
)
default_projects = os.environ.get(
    "PENPAL_PROJECT_DIR", os.path.join(default_workspace, "projects")
)
default_runner = os.environ.get(
    "PENPAL_RUNNER_SCRIPT_PATH", os.path.join(default_workspace, "tools", "runner.py")
)

parser = argparse.ArgumentParser()
parser.add_argument(
    "--gallery-dir", default=default_gallery, help="Path to gallery directory"
)
parser.add_argument(
    "--project-dir", default=default_projects, help="Path to projects directory"
)
parser.add_argument(
    "--runner-script-path",
    default=default_runner,
    help="Path to runner script (e.g. tools/runner.py)",
)
args, _ = parser.parse_known_args()

GALLERY_DIR = os.path.abspath(args.gallery_dir)
PROJECTS_DIR = os.path.abspath(args.project_dir)
RUNNER_SCRIPT_PATH = os.path.abspath(args.runner_script_path)

st.set_page_config(layout="wide", page_title="Creative Coding Dashboard")


def get_git_message(repo_path, commit_hash):
    try:
        # Check if the hash is in the repo
        return (
            subprocess.check_output(
                ["git", "show", "-s", "--format=%B", commit_hash], cwd=repo_path
            )
            .strip()
            .decode("utf-8")
        )
    except subprocess.CalledProcessError:
        return "Unknown commit or no git repository"


def get_projects():
    if not os.path.exists(PROJECTS_DIR):
        return []
    projects = []
    for d in os.listdir(PROJECTS_DIR):
        if os.path.isdir(os.path.join(PROJECTS_DIR, d)):
            projects.append(d)
    return sorted(projects)


def read_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}


def format_compact_json(obj, level=0, indent=2):
    ind = " " * (level * indent)
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        items = []
        for k, v in obj.items():
            key_str = json.dumps(k)
            val_str = format_compact_json(v, level + 1, indent)
            items.append(f"{ind}{' ' * indent}{key_str}: {val_str}")
        return "{\n" + ",\n".join(items) + "\n" + ind + "}"
    elif isinstance(obj, list):
        if not obj:
            return "[]"
        has_complex = any(isinstance(r, (list, dict)) for r in obj)
        if not has_complex:
            elements = [json.dumps(r) for r in obj]
            return "[" + ", ".join(elements) + "]"
        else:
            items = []
            for v in obj:
                items.append(
                    f"{ind}{' ' * indent}{format_compact_json(v, level + 1, indent)}"
                )
            return "[\n" + ",\n".join(items) + "\n" + ind + "]"
    else:
        return json.dumps(obj)


st.title("Creative Coding Dashboard")

projects = get_projects()
if not projects:
    st.warning("No projects found in projects/ directory.")
    st.stop()

if "project_index" not in st.session_state:
    st.session_state.project_index = 0


def go_prev():
    st.session_state.project_index = (st.session_state.project_index - 1) % len(
        projects
    )


def go_next():
    st.session_state.project_index = (st.session_state.project_index + 1) % len(
        projects
    )


def on_select():
    st.session_state.project_index = projects.index(st.session_state.project_selectbox)


st.sidebar.subheader("Navigation")
nav_cols = st.sidebar.columns(2)
nav_cols[0].button("⬅️ Prev", on_click=go_prev, use_container_width=True)
nav_cols[1].button("Next ➡️", on_click=go_next, use_container_width=True)

if st.session_state.project_index >= len(projects):
    st.session_state.project_index = 0

selected_project = st.sidebar.selectbox(
    "Select Project",
    projects,
    index=st.session_state.project_index,
    key="project_selectbox",
    on_change=on_select,
)

if selected_project is None:
    st.warning("No project selected.")
    st.stop()

project_path = os.path.join(PROJECTS_DIR, selected_project)

mode = st.sidebar.radio("View Mode", ["Regular Outputs", "Test Outputs"])
show_details = st.sidebar.checkbox("Show Details", value=False)

st.sidebar.divider()
st.sidebar.subheader("View Settings")
global_zoom = st.sidebar.slider(
    "Image Zoom (%)", min_value=10, max_value=500, value=100, step=10
)
skip_delete_confirm = st.sidebar.checkbox("Skip Delete Confirmation", value=False)
items_per_page = st.sidebar.selectbox("Items per page", [10, 25, 50, 100], index=1)


def display_output(svg_path, metadata_path, git_hash=None, git_msg=None):
    with st.container():
        if show_details:
            cols = st.columns([2, 1])
            img_col = cols[0]
            details_col = cols[1]
        else:
            img_col = st.container()
            details_col = None

        with img_col:
            try:
                png_path = svg_path.replace(".svg", ".png")
                b64 = None

                if not os.path.exists(png_path):
                    with open(svg_path, "r") as f:
                        svg_content = f.read()
                    if cairosvg is not None:
                        try:
                            cairosvg.svg2png(
                                bytestring=svg_content.encode("utf-8"),
                                write_to=png_path,
                            )
                        except Exception as e:
                            st.warning(f"Failed to cache SVG to PNG: {e}")

                if os.path.exists(png_path):
                    with open(png_path, "rb") as f:
                        png_content = f.read()
                    b64 = base64.b64encode(png_content).decode("utf-8")
                    img_src = f"data:image/png;base64,{b64}"
                else:
                    # Fallback to SVG if PNG caching failed or cairosvg isn't installed
                    with open(svg_path, "r") as f:
                        svg_content = f.read()
                    b64 = base64.b64encode(svg_content.encode("utf-8")).decode("utf-8")
                    img_src = f"data:image/svg+xml;base64,{b64}"

                html = f'<div style="width:{global_zoom}%; max-width: none;"><img src="{img_src}" style="width:100%; border:1px solid #ddd;"/></div>'
                st.markdown(html, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Could not load image: {e}")

        if details_col is not None:
            with details_col:
                st.subheader("Details")
                if git_hash:
                    st.write(f"**Git Hash:** `{git_hash}`")

                metadata = read_json(metadata_path)

                # Extract hash and timestamp from filename
                # Filename format: {timestamp}_{hash}.svg
                basename = os.path.basename(svg_path)
                name_parts = os.path.splitext(basename)[0].split("_")
                if len(name_parts) >= 2:
                    ts = name_parts[0]
                    # Format timestamp nicely if possible
                    formatted_ts = ts
                    if len(ts) == 14:  # YYYYMMDDHHMMSS
                        formatted_ts = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}:{ts[12:14]}"

                    st.write(f"**Param Hash:** `{name_parts[1]}`")
                    st.write(f"**Date:** {formatted_ts}")

                with st.expander("Parameters", expanded=False):
                    st.text(format_compact_json(metadata.get("params", {})))

                # Like / Dislike
                rating = metadata.get("rating", "none")
                st.write("**Rating:**")
                r_cols = st.columns(3)
                if r_cols[0].button(
                    "👍" + (" (Active)" if rating == "like" else ""),
                    key=f"like_{svg_path}",
                ):
                    metadata["rating"] = "like" if rating != "like" else "none"
                    with open(metadata_path, "w") as f:
                        json.dump(metadata, f, indent=2)
                    st.rerun()
                if r_cols[1].button(
                    "👎" + (" (Active)" if rating == "dislike" else ""),
                    key=f"dislike_{svg_path}",
                ):
                    metadata["rating"] = "dislike" if rating != "dislike" else "none"
                    with open(metadata_path, "w") as f:
                        json.dump(metadata, f, indent=2)
                    st.rerun()

                st.write("**Actions:**")
                a_cols = st.columns(2)
                # Button to rerun this exact output in test mode
                if a_cols[0].button("Rerun as Test", key=f"btn_{svg_path}"):
                    with st.spinner("Rerunning..."):
                        params_json = json.dumps(metadata.get("params", {}))
                        # Use the correct python binary
                        python_bin = sys.executable if sys.executable else "python"
                        cmd = [
                            python_bin,
                            RUNNER_SCRIPT_PATH,
                            selected_project,
                            "--project-dir",
                            PROJECTS_DIR,
                            "--gallery-dir",
                            GALLERY_DIR,
                            "--dev",
                            "--params",
                            params_json,
                        ]
                        res = subprocess.run(
                            cmd,
                            cwd=os.path.dirname(PROJECTS_DIR),
                            capture_output=True,
                            text=True,
                        )
                        if res.returncode == 0:
                            st.success("Test run completed!")
                            # It will appear in Test Outputs mode
                        else:
                            st.error(f"Error: {res.stderr}\\n\\n{res.stdout}")

                # Delete logic
                if a_cols[1].button("🗑️ Delete", type="primary", key=f"del_{svg_path}"):
                    if skip_delete_confirm:
                        try:
                            os.remove(svg_path)
                            if os.path.exists(metadata_path):
                                os.remove(metadata_path)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete: {e}")
                    else:

                        @st.dialog("Confirm Deletion")
                        def confirm_deletion():
                            st.warning(
                                "Are you sure you want to delete this artwork? This action cannot be undone."
                            )
                            c1, c2 = st.columns(2)
                            if c1.button("Yes, Delete"):
                                try:
                                    os.remove(svg_path)
                                    if os.path.exists(metadata_path):
                                        os.remove(metadata_path)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to delete: {e}")
                            if c2.button("Cancel"):
                                st.rerun()

                        confirm_deletion()
        st.divider()


if mode == "Regular Outputs":
    outputs_dir = os.path.join(GALLERY_DIR, selected_project, "svg")
    if not os.path.exists(outputs_dir):
        st.info("No regular outputs found for this project.")
    else:
        # Get all git hash directories
        hashes = [
            d
            for d in os.listdir(outputs_dir)
            if os.path.isdir(os.path.join(outputs_dir, d))
        ]
        if not hashes:
            st.info("No regular outputs found.")
        else:
            # Find the hash with the most recent modification time (checking all files inside)
            def get_latest_mtime(hash_dir_name):
                full_path = os.path.join(outputs_dir, hash_dir_name)
                files = glob.glob(os.path.join(full_path, "*"))
                if not files:
                    return 0
                return max(os.path.getmtime(f) for f in files)

            # Sort hashes by latest modification time, descending
            hashes.sort(key=get_latest_mtime, reverse=True)

            selected_hash = st.selectbox("Select Git Hash", hashes, index=0)
            hash_dir = os.path.join(outputs_dir, selected_hash)
            git_msg = get_git_message(project_path, selected_hash)

            st.subheader(f"Outputs for Commit `{selected_hash}`")
            st.write(f"> {git_msg}")

            svg_files = sorted(glob.glob(os.path.join(hash_dir, "*.svg")), reverse=True)

            # Pagination
            total_items = len(svg_files)
            if total_items == 0:
                st.info("No SVG files found for this commit.")
            else:
                total_pages = max(
                    1, (total_items + items_per_page - 1) // items_per_page
                )
                page = st.number_input(
                    "Page", min_value=1, max_value=total_pages, value=1
                )
                st.write(
                    f"Showing page {page} of {total_pages} ({total_items} total items)"
                )

                start_idx = (page - 1) * items_per_page
                end_idx = start_idx + items_per_page
                current_svgs = svg_files[start_idx:end_idx]

                for svg_file in current_svgs:
                    json_file = svg_file.replace(".svg", ".json")
                    if os.path.exists(json_file):
                        display_output(svg_file, json_file, selected_hash, git_msg)

elif mode == "Test Outputs":
    test_outputs_dir = os.path.join(GALLERY_DIR, selected_project, "test")

    st.subheader("Run New Test")

    # Try to load default params from example.json
    default_params = "{\n  \n}"
    params_json_path = os.path.join(project_path, "example.json")

    if os.path.exists(params_json_path):
        try:
            with open(params_json_path, "r") as f:
                params_data = json.load(f)
            if isinstance(params_data, list) and len(params_data) > 0:
                params_data = params_data[0]
            if params_data is not None:
                default_params = format_compact_json(params_data)
        except Exception as e:
            st.warning(f"Failed to load example.json defaults: {e}")

    params_input = st.text_area(
        "Parameters (JSON format)", value=default_params, height=500
    )

    if st.button("Run Test with Parameters", type="primary"):
        try:
            parsed = json.loads(params_input)
            with st.spinner("Running..."):
                python_bin = sys.executable if sys.executable else "python"
                cmd = [
                    python_bin,
                    RUNNER_SCRIPT_PATH,
                    selected_project,
                    "--project-dir",
                    PROJECTS_DIR,
                    "--gallery-dir",
                    GALLERY_DIR,
                    "--dev",
                    "--params",
                    params_input,
                ]
                res = subprocess.run(
                    cmd,
                    cwd=os.path.dirname(PROJECTS_DIR),
                    capture_output=True,
                    text=True,
                )
                if res.returncode == 0:
                    st.success("Test run successful!")
                else:
                    st.error(f"Test run failed:\n\n{res.stderr}\n{res.stdout}")
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON format in parameters: {e}")

    st.divider()
    st.subheader("Previous Test Outputs")
    if not os.path.exists(test_outputs_dir):
        st.info("No test outputs found.")
    else:
        timestamp_dirs = sorted(
            [
                d
                for d in os.listdir(test_outputs_dir)
                if os.path.isdir(os.path.join(test_outputs_dir, d))
            ],
            reverse=True,
        )
        # Flatten all svgs from all timestamp dirs, sort by modification time so newest is first
        all_test_svgs = []
        for ts_dir in timestamp_dirs:
            full_ts_dir = os.path.join(test_outputs_dir, ts_dir)
            svg_files = glob.glob(os.path.join(full_ts_dir, "*.svg"))
            for s in svg_files:
                all_test_svgs.append((os.path.getmtime(s), ts_dir, s))

        all_test_svgs.sort(key=lambda x: x[0], reverse=True)

        total_items = len(all_test_svgs)
        if total_items == 0:
            st.info("No test outputs found.")
        else:
            total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
            page = st.number_input(
                "Test Outputs Page",
                min_value=1,
                max_value=total_pages,
                value=1,
                key="test_page",
            )
            st.write(
                f"Showing page {page} of {total_pages} ({total_items} total items)"
            )

            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            current_test_svgs = all_test_svgs[start_idx:end_idx]

            for mtime, ts_dir, svg_file in current_test_svgs:
                json_file = svg_file.replace(".svg", ".json")
                if os.path.exists(json_file):
                    st.write(f"**Run at:** {ts_dir}")
                    display_output(svg_file, json_file)
