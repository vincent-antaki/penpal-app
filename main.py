import streamlit as st
import os
import glob
import json
import subprocess
import sys
import argparse


# Default locations
default_workspace = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
default_gallery = os.environ.get("PENPAL_GALLERY_DIR", os.path.join(default_workspace, "gallery"))
default_projects = os.environ.get("PENPAL_PROJECT_DIR", os.path.join(default_workspace, "projects"))
default_runner = os.environ.get("PENPAL_RUNNER_SCRIPT_PATH", os.path.join(default_workspace, "tools", "runner.py"))

parser = argparse.ArgumentParser()
parser.add_argument("--gallery-dir", default=default_gallery, help="Path to gallery directory")
parser.add_argument("--project-dir", default=default_projects, help="Path to projects directory")
parser.add_argument("--runner-script-path", default=default_runner, help="Path to runner script (e.g. tools/runner.py)")
args, _ = parser.parse_known_args()

GALLERY_DIR = os.path.abspath(args.gallery_dir)
PROJECTS_DIR = os.path.abspath(args.project_dir)
RUNNER_SCRIPT_PATH = os.path.abspath(args.runner_script_path)

st.set_page_config(layout="wide", page_title="Creative Coding Dashboard")

def get_git_message(repo_path, commit_hash):
    try:
        # Check if the hash is in the repo
        return subprocess.check_output(['git', 'show', '-s', '--format=%B', commit_hash], cwd=repo_path).strip().decode('utf-8')
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
                items.append(f"{ind}{' ' * indent}{format_compact_json(v, level + 1, indent)}")
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
    st.session_state.project_index = (st.session_state.project_index - 1) % len(projects)

def go_next():
    st.session_state.project_index = (st.session_state.project_index + 1) % len(projects)

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
    on_change=on_select
)
project_path = os.path.join(PROJECTS_DIR, selected_project)

mode = st.sidebar.radio("View Mode", ["Regular Outputs", "Test Outputs"])
show_details = st.sidebar.checkbox("Show Details", value=False)

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
                with open(svg_path, "r") as f:
                    svg_content = f.read()
                # To display SVG directly without caching issues, we can use markdown with base64 or just html
                import base64
                b64 = base64.b64encode(svg_content.encode('utf-8')).decode("utf-8")
                html = f'<img src="data:image/svg+xml;base64,{b64}" style="width:100%; border:1px solid #ddd;"/>'
                st.markdown(html, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Could not load SVG: {e}")
        
        if details_col is not None:
            with details_col:
                st.subheader("Details")
                if git_hash:
                    st.write(f"**Git Hash:** `{git_hash}`")
                    if git_msg:
                        st.write(f"**Message:** {git_msg}")
                
                metadata = read_json(metadata_path)
                st.write("**Parameters:**")
                st.json(metadata.get("params", {}))
                
                # Button to rerun this exact output in test mode
                if st.button("Rerun as Test", key=f"btn_{svg_path}"):
                    with st.spinner("Rerunning..."):
                        params_json = json.dumps(metadata.get("params", {}))
                        # Use the correct python binary
                        python_bin = sys.executable if sys.executable else 'python'
                        cmd = [python_bin, RUNNER_SCRIPT_PATH, selected_project, '--project-dir', PROJECTS_DIR, '--gallery-dir', GALLERY_DIR, '--dev', '--params', params_json]
                        res = subprocess.run(cmd, cwd=os.path.dirname(PROJECTS_DIR), capture_output=True, text=True)
                        if res.returncode == 0:
                            st.success("Test run completed!")
                            # It will appear in Test Outputs mode
                        else:
                            st.error(f"Error: {res.stderr}\\n\\n{res.stdout}")
        st.divider()

if mode == "Regular Outputs":
    outputs_dir = os.path.join(GALLERY_DIR, selected_project, "svg")
    if not os.path.exists(outputs_dir):
        st.info("No regular outputs found for this project.")
    else:
        # Get all git hash directories
        hashes = [d for d in os.listdir(outputs_dir) if os.path.isdir(os.path.join(outputs_dir, d))]
        if not hashes:
            st.info("No regular outputs found.")
        else:
            selected_hash = st.selectbox("Select Git Hash", hashes)
            hash_dir = os.path.join(outputs_dir, selected_hash)
            git_msg = get_git_message(project_path, selected_hash)
            
            st.subheader(f"Outputs for Commit `{selected_hash}`")
            st.write(f"> {git_msg}")
            
            svg_files = glob.glob(os.path.join(hash_dir, "*.svg"))
            for svg_file in sorted(svg_files, reverse=True): 
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
            
    params_input = st.text_area("Parameters (JSON format)", value=default_params, height=500)
    
    if st.button("Run Test with Parameters", type="primary"):
        try:
            parsed = json.loads(params_input)
            with st.spinner("Running..."):
                python_bin = sys.executable if sys.executable else 'python'
                cmd = [python_bin, RUNNER_SCRIPT_PATH, selected_project, '--project-dir', PROJECTS_DIR, '--gallery-dir', GALLERY_DIR, '--dev', '--params', params_input]
                res = subprocess.run(cmd, cwd=os.path.dirname(PROJECTS_DIR), capture_output=True, text=True)
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
        timestamp_dirs = sorted([d for d in os.listdir(test_outputs_dir) if os.path.isdir(os.path.join(test_outputs_dir, d))], reverse=True)
        # Flatten all svgs from all timestamp dirs, sort by modification time so newest is first
        all_test_svgs = []
        for ts_dir in timestamp_dirs:
            full_ts_dir = os.path.join(test_outputs_dir, ts_dir)
            svg_files = glob.glob(os.path.join(full_ts_dir, "*.svg"))
            for s in svg_files:
                all_test_svgs.append((os.path.getmtime(s), ts_dir, s))
                
        all_test_svgs.sort(key=lambda x: x[0], reverse=True)
        
        for mtime, ts_dir, svg_file in all_test_svgs:
            json_file = svg_file.replace(".svg", ".json")
            if os.path.exists(json_file):
                st.write(f"**Run at:** {ts_dir}")
                display_output(svg_file, json_file)
