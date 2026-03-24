"""GitHub write tools — create issues, branches, commit files, open PRs."""

import os
import re
import subprocess
from crewai.tools import BaseTool
from github import Github


def _get_github_client() -> Github:
    token = os.environ["GITHUB_TOKEN"]
    return Github(token)


def _parse_repo_slug(repo_url: str) -> str:
    """Extract 'owner/repo' from a GitHub URL."""
    match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", repo_url)
    if not match:
        raise ValueError(f"Cannot parse repo slug from: {repo_url}")
    return match.group(1)


class CreateIssueTool(BaseTool):
    """Creates a GitHub Issue with the provided title and body."""

    name: str = "Create GitHub Issue"
    description: str = (
        "Creates a GitHub Issue in the repository. "
        "Input format: 'REPO_URL|||TITLE|||BODY' "
        "Returns: issue URL and issue number, e.g. 'Issue #42 created: https://...'"
    )

    def _run(self, tool_input: str) -> str:
        repo_url, title, body = tool_input.split("|||", 2)
        slug = _parse_repo_slug(repo_url.strip())
        repo = _get_github_client().get_repo(slug)
        issue = repo.create_issue(title=title.strip(), body=body.strip())
        return f"Issue #{issue.number} created: {issue.html_url}"


class CreateBranchTool(BaseTool):
    """Creates a new git branch in a local repository clone."""

    name: str = "Create Feature Branch"
    description: str = (
        "Creates a new git branch in the local repository clone. "
        "Input format: 'CLONE_PATH|||BRANCH_NAME' "
        "Returns: confirmation message."
    )

    def _run(self, tool_input: str) -> str:
        clone_path, branch_name = tool_input.split("|||", 1)
        result = subprocess.run(
            ["git", "checkout", "-b", branch_name.strip()],
            cwd=clone_path.strip(),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return f"ERROR: {result.stderr.strip()}"
        return f"Branch '{branch_name.strip()}' created successfully."


class CommitAndPushTool(BaseTool):
    """Stages all changes in a local clone, commits, and pushes to remote."""

    name: str = "Commit and Push Changes"
    description: str = (
        "Stages all changed files, commits them, and pushes to the remote branch. "
        "Input format: 'CLONE_PATH|||COMMIT_MESSAGE' "
        "Returns: confirmation with pushed branch name."
    )

    def _run(self, tool_input: str) -> str:
        clone_path, commit_message = tool_input.split("|||", 1)
        cwd = clone_path.strip()

        subprocess.run(["git", "add", "-A"], cwd=cwd, check=True)

        commit = subprocess.run(
            ["git", "commit", "-m", commit_message.strip()],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        if commit.returncode != 0:
            return f"ERROR on commit: {commit.stderr.strip()}"

        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
        ).stdout.strip()

        push = subprocess.run(
            ["git", "push", "origin", branch],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        if push.returncode != 0:
            return f"ERROR on push: {push.stderr.strip()}"

        return f"Pushed branch '{branch}' to remote successfully."


class CreatePRTool(BaseTool):
    """Opens a Pull Request on GitHub from a feature branch to the default branch."""

    name: str = "Create Pull Request"
    description: str = (
        "Creates a Pull Request on GitHub. "
        "Input format: 'REPO_URL|||BRANCH_NAME|||PR_TITLE|||PR_BODY' "
        "Returns: PR URL."
    )

    def _run(self, tool_input: str) -> str:
        repo_url, branch, title, body = tool_input.split("|||", 3)
        slug = _parse_repo_slug(repo_url.strip())
        repo = _get_github_client().get_repo(slug)
        pr = repo.create_pull(
            title=title.strip(),
            body=body.strip(),
            head=branch.strip(),
            base=repo.default_branch,
        )
        return f"PR #{pr.number} created: {pr.html_url}"
