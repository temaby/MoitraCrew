"""GitHub tools for cloning repositories for local analysis."""

import os
import subprocess
import tempfile
from crewai.tools import BaseTool


class CloneRepoTool(BaseTool):
    """Clones a GitHub repository to a local temp directory for analysis."""

    name: str = "Clone GitHub Repository"
    description: str = (
        "Clones a GitHub repository locally for analysis. "
        "Input: GitHub repo URL (e.g. https://github.com/owner/repo). "
        "Returns: absolute path to the cloned repository on disk. "
        "Use this path with DirectoryReadTool and FileReadTool to explore the code."
    )

    def _run(self, repo_url: str) -> str:
        token = os.getenv("GITHUB_TOKEN", "")
        tmp_dir = tempfile.mkdtemp(prefix="moitracrew_repo_")

        # Inject token into URL for private repos
        clone_url = repo_url
        if token and "github.com" in repo_url:
            clone_url = repo_url.replace(
                "https://github.com",
                f"https://{token}@github.com",
            )

        result = subprocess.run(
            ["git", "clone", "--depth=1", clone_url, tmp_dir],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return f"ERROR: Clone failed — {result.stderr.strip()}"

        # Store path for cleanup by main.py
        _set_last_clone_path(tmp_dir)
        return tmp_dir


# Module-level storage so main.py can clean up the temp dir after the crew finishes
_last_clone_path: str = ""


def _set_last_clone_path(path: str) -> None:
    global _last_clone_path
    _last_clone_path = path


def get_last_clone_path() -> str:
    return _last_clone_path
