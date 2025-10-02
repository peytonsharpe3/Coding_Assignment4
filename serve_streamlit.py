# serve_streamlit.py
import shlex, subprocess
from pathlib import Path
import modal

app = modal.App("my-streamlit-app")

PROJECT_ROOT = Path(__file__).parent
REMOTE_SCRIPT = "/app/streamlit_app.py"

# IMPORTANT: Do ALL build steps first, then add_local_file LAST.
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "streamlit>=1.35",
        "pandas>=2.2",
        "supabase>=2.6",
        "altair>=5.0",
        "pyarrow>=15",
    )
    .add_local_file(str(PROJECT_ROOT / "streamlit_app.py"), REMOTE_SCRIPT)  # LAST step
)

# You already created this secret: streamlit-env
@app.function(image=image, secrets=[modal.Secret.from_name("streamlit-env")])
@modal.web_server(8000)
def run():
    cmd = (
        f"streamlit run {shlex.quote(REMOTE_SCRIPT)} "
        f"--server.port 8000 --server.address 0.0.0.0 "
        f"--server.enableCORS=false --server.enableXsrfProtection=false"
    )
    subprocess.Popen(cmd, shell=True)