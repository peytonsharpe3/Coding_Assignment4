import shlex, subprocess
from pathlib import Path
import modal

app = modal.App("quotes-streamlit-on-modal")

PROJECT_ROOT = Path(__file__).parent
REMOTE_DIR = "/root/app"
REMOTE_SCRIPT = f"{REMOTE_DIR}/streamlit_app.py"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements(str(PROJECT_ROOT / "requirements.txt"))
    .add_local_dir(str(PROJECT_ROOT), REMOTE_DIR, exclude=[".git", ".env", "__pycache__", ".modal"])
)

# Create this secret once:
# modal secret create supabase-env SUPABASE_URL=... SUPABASE_KEY=...
@app.function(image=image, secrets=[modal.Secret.from_name("supabase-env")])
@modal.web_server(8000)
def run():
    cmd = (
        f"streamlit run {shlex.quote(REMOTE_SCRIPT)} "
        f"--server.port 8000 --server.address 0.0.0.0 "
        f"--server.enableCORS=false --server.enableXsrfProtection=false"
    )
    # Run as background process so Modal can keep the server alive
    subprocess.Popen(cmd, shell=True)
