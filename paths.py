"""Project path definitions resolved relative to this file."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"
TRACES_DIR = PROJECT_ROOT / "traces"
WORKSPACE_DIR = PROJECT_ROOT / "workspace"
MEMORY_DIR = PROJECT_ROOT / "memory"
OUTPUT_SUBDIR = "output"
SKILLS_SUBDIR = "skills"


def ensure_workspace(workspace_dir: Path | None = None) -> Path:
    """Ensure workspace directories exist."""
    ws = workspace_dir or WORKSPACE_DIR
    ws.mkdir(parents=True, exist_ok=True)
    (ws / OUTPUT_SUBDIR).mkdir(parents=True, exist_ok=True)
    (ws / SKILLS_SUBDIR).mkdir(parents=True, exist_ok=True)
    return ws
