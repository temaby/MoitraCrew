"""MoitraFlow — orchestrates the full development cycle with test feedback loop."""

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from pydantic import BaseModel
from crewai.flow.flow import Flow, listen, router, start

from crew import MoitraCrew
from tools.github_tools import get_last_clone_path, _set_last_clone_path
from tools.test_tools import RunTestsTool


# Test command detection patterns — ordered by priority
_TEST_COMMAND_PATTERNS = [
    (["pytest", "python", "fastapi", "flask", "django"], "pytest"),
    (["npm", "react", "node", "typescript", "javascript", "vue", "angular"], "npm test -- --watchAll=false"),
    (["dotnet", "c#", "asp.net", "csharp"], "dotnet test"),
    (["go ", "golang"], "go test ./..."),
    (["cargo", "rust"], "cargo test"),
    (["maven", "gradle", "java", "spring"], "mvn test"),
]

DEFAULT_TEST_COMMAND = "pytest"
DEFAULT_PROJECT_PREFIX = "PROJ"
_OUTPUT_DIR = Path(__file__).parent / "output"
_LAST_RUN_FILE = _OUTPUT_DIR / ".last_run.json"


def _save_run_state(clone_path: str, issue_number: str, repo_url: str, test_command: str) -> None:
    """Persist planning outputs so dev-only runs can skip planning."""
    _LAST_RUN_FILE.parent.mkdir(exist_ok=True)
    _LAST_RUN_FILE.write_text(
        json.dumps({
            "clone_path": clone_path,
            "issue_number": issue_number,
            "repo_url": repo_url,
            "test_command": test_command,
        }),
        encoding="utf-8",
    )


def _load_run_state() -> dict | None:
    """Load previously saved planning state. Returns None if not found or stale."""
    if not _LAST_RUN_FILE.exists():
        return None
    try:
        return json.loads(_LAST_RUN_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, KeyError):
        return None


def _compute_project_prefix(repo_url: str) -> str:
    """
    Derive a 4-letter uppercase prefix from the repository name.
    Examples:
      inex                → INEX  (1 word, take 4 chars)
      billing-service     → BILS  (2 words: 2+2 chars)
      my-expense-tracker  → MYET  (3 words: 2+1+1)
      some-long-proj-name → SLPN  (4+ words: 1 per word)
    """
    slug = repo_url.rstrip("/").split("/")[-1]
    slug = re.sub(r"\.git$", "", slug)
    words = [w for w in re.split(r"[-_.\s]+", slug) if w]

    if not words:
        return DEFAULT_PROJECT_PREFIX

    n = len(words)
    if n == 1:
        prefix = words[0][:4]
    elif n == 2:
        prefix = words[0][:2] + words[1][:2]
    elif n == 3:
        prefix = words[0][:2] + words[1][:1] + words[2][:1]
    else:
        prefix = "".join(w[0] for w in words)[:4]

    return prefix.upper() or DEFAULT_PROJECT_PREFIX


def _detect_test_command(repo_analysis: str) -> str:
    """Detect the appropriate test command from the repo analysis output."""
    lower = repo_analysis.lower()
    for keywords, command in _TEST_COMMAND_PATTERNS:
        if any(kw in lower for kw in keywords):
            return command
    return DEFAULT_TEST_COMMAND


class MoitraFlowState(BaseModel):
    # User inputs
    user_idea: str = ""
    repo_url: str = ""

    # Filled during execution
    clone_path: str = ""
    issue_number: str = ""
    branch_name: str = ""
    test_command: str = DEFAULT_TEST_COMMAND

    # Skip planning and reuse outputs from previous run (dev-only debug mode)
    skip_planning: bool = False

    # Architecture spec from planning — passed to dev so it knows what to build
    architecture_spec: str = ""

    # Dev output — list of written files passed to code review
    implementation_summary: str = ""

    # Test feedback loop
    retry_count: int = 0
    max_retries: int = 3
    tests_passed: bool = False
    last_test_output: str = ""


class MoitraFlow(Flow[MoitraFlowState]):
    """
    Full development cycle:
      planning → dev + test loop → publish PR (on pass) or report failure (on fail)
    """

    @start()
    def run_planning(self):
        """Analyze repo, write User Stories, create GitHub Issue, design architecture.

        In skip_planning mode: reuses outputs from the previous run instead of
        re-cloning and re-running the planning crew.
        """
        if self.state.skip_planning:
            return self._restore_planning_state()

        inputs = {
            "user_idea": self.state.user_idea,
            "repo_url": self.state.repo_url,
            "tech_stack_hint": "",
            "repo_context": "",
        }

        result = MoitraCrew().planning_crew().kickoff(inputs=inputs)

        # clone_path is stored by CloneRepoTool after analyze_repository runs
        self.state.clone_path = get_last_clone_path()

        # Auto-detect test command from repo analysis output
        self.state.test_command = _detect_test_command(str(result))

        # Extract issue number from structured output of create_github_issue task
        if result.pydantic and hasattr(result.pydantic, "issue_number"):
            self.state.issue_number = str(result.pydantic.issue_number)
        else:
            # Fallback: parse from raw text if pydantic output unavailable
            match = re.search(r"Issue #(\d+)", str(result))
            if match:
                self.state.issue_number = match.group(1)

        # Read architecture spec so Dev crew can access it (separate crew has no shared context)
        # Truncate to 12000 chars to avoid oversized prompts — architecture docs can be very long
        arch_file = _OUTPUT_DIR / "02_architecture.md"
        if arch_file.exists():
            self.state.architecture_spec = arch_file.read_text(encoding="utf-8")

        # Persist state for future dev-only runs
        _save_run_state(
            clone_path=self.state.clone_path,
            issue_number=self.state.issue_number,
            repo_url=self.state.repo_url,
            test_command=self.state.test_command,
        )

        return result

    def _restore_planning_state(self) -> str:
        """Restore state from previous run. Re-clones repo if temp dir is gone."""
        saved = _load_run_state()
        if not saved:
            raise RuntimeError(
                "No previous run found. Run in full mode first to generate planning outputs."
            )

        print("\n[dev-only] Reusing planning outputs from previous run.")

        # Restore cheap fields from saved state
        self.state.issue_number = saved["issue_number"]
        self.state.test_command = saved["test_command"]

        # Re-use clone dir if still on disk; otherwise re-clone (no full analysis)
        clone_path = saved["clone_path"]
        if Path(clone_path).exists():
            print(f"[dev-only] Reusing existing clone at: {clone_path}")
            self.state.clone_path = clone_path
            _set_last_clone_path(clone_path)
        else:
            print("[dev-only] Temp clone dir is gone — re-cloning repository...")
            token = os.getenv("GITHUB_TOKEN", "")
            tmp_dir = tempfile.mkdtemp(prefix="moitracrew_repo_")
            repo_url = saved["repo_url"]
            clone_url = repo_url
            if token and "github.com" in repo_url:
                clone_url = repo_url.replace("https://github.com", f"https://{token}@github.com")
            result = subprocess.run(
                ["git", "clone", "--depth=1", clone_url, tmp_dir],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Re-clone failed: {result.stderr.strip()}")
            self.state.clone_path = tmp_dir
            _set_last_clone_path(tmp_dir)
            print(f"[dev-only] Re-cloned to: {tmp_dir}")

        # Load architecture spec from saved output file
        arch_file = _OUTPUT_DIR / "02_architecture.md"
        if arch_file.exists():
            self.state.architecture_spec = arch_file.read_text(encoding="utf-8")
        else:
            print("[dev-only] WARNING: 02_architecture.md not found — Dev will lack the spec.")

        return "reused"

    @listen(run_planning)
    def run_dev_and_test_loop(self, _):
        """
        Dev implements the feature, QA writes tests, then tests are run.
        If tests fail, Dev gets the error output and fixes the code.
        Repeats up to max_retries times.

        Note: implemented as a Python loop rather than @router cycling to avoid
        a known bug in CrewAI 1.11.x where circular router flows stop prematurely.
        """
        crew = MoitraCrew()
        test_tool = RunTestsTool()

        base_inputs = {
            "clone_path": self.state.clone_path,
            "repo_url": self.state.repo_url,
            "issue_number": self.state.issue_number,
            "test_command": self.state.test_command,
        }

        # Initial implementation
        branch_name = f"feature/issue-{self.state.issue_number}-implementation"
        self.state.branch_name = branch_name

        dev_inputs = {**base_inputs, "branch_name": branch_name, "architecture_spec": self.state.architecture_spec}
        dev_result = crew.dev_crew().kickoff(inputs=dev_inputs)
        self.state.implementation_summary = str(dev_result)

        # Code review → fix loop (up to max_retries)
        review_inputs = {
            "clone_path": self.state.clone_path,
            "implementation_summary": self.state.implementation_summary,
        }
        for review_attempt in range(self.state.max_retries):
            review_output = crew.review_crew().kickoff(inputs=review_inputs)
            review = review_output.pydantic  # ReviewResult | None

            if review is not None:
                approved = review.status == "APPROVED"
                review_text = "\n".join(review.issues) if review.issues else ""
            else:
                # Fallback if structured output failed
                review_text = str(review_output)
                approved = "CHANGES_REQUESTED" not in review_text

            if approved:
                print("\n[Code review] APPROVED — proceeding to tests.")
                break

            print(f"\n[Code review attempt {review_attempt + 1}] Changes requested — sending to Dev for fixes.")
            crew.fix_crew().kickoff(inputs={
                "clone_path": self.state.clone_path,
                "test_output": review_text,
            })
        else:
            # Exhausted review retries without approval
            print(f"\n[Code review] Still not approved after {self.state.max_retries} attempts — proceeding anyway.")

        # QA writes test files
        crew.qa_crew().kickoff(inputs=base_inputs)

        # Test → fix loop
        for attempt in range(self.state.max_retries):
            self.state.retry_count = attempt + 1

            test_result = test_tool._run(
                f"{self.state.clone_path}|||{self.state.test_command}"
            )
            self.state.last_test_output = test_result

            print(f"\n[Test attempt {self.state.retry_count}/{self.state.max_retries}] {test_result[:80]}...")

            if test_result.startswith("PASSED"):
                self.state.tests_passed = True
                return "pass"

            # Tests failed — send Dev the error output for fixes
            if attempt < self.state.max_retries - 1:
                print(f"\n[Tests failed] Sending error output to Dev for fixes (attempt {attempt + 1})...")
                fix_inputs = {
                    "clone_path": self.state.clone_path,
                    "test_output": test_result,
                }
                crew.fix_crew().kickoff(inputs=fix_inputs)

        self.state.tests_passed = False
        return "fail"

    @router(run_dev_and_test_loop)
    def check_test_result(self, result):
        """Route to publish on pass, report failure on fail."""
        return result  # "pass" or "fail"

    @listen("pass")
    def publish(self, _):
        """Tests passed — commit all changes, push, and open a Pull Request."""
        publish_inputs = {
            "clone_path": self.state.clone_path,
            "repo_url": self.state.repo_url,
            "issue_number": self.state.issue_number,
            "branch_name": self.state.branch_name,
        }
        MoitraCrew().publish_crew().kickoff(inputs=publish_inputs)

    @listen("fail")
    def report_failure(self, _):
        """All retries exhausted — save failure report and notify user."""
        failure_path = _OUTPUT_DIR / "test_failure.txt"
        failure_path.write_text(self.state.last_test_output, encoding="utf-8")

        print(f"\n{'=' * 60}")
        print(f"FAILURE: Tests did not pass after {self.state.max_retries} attempts.")
        print(f"Last test output saved to: {failure_path.resolve()}")
        print(f"{'=' * 60}")
