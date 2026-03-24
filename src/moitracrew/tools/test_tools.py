"""Tools for running test suites in a local repository clone."""

import subprocess
from crewai.tools import BaseTool


class RunTestsTool(BaseTool):
    """Runs the test suite in a local repository directory."""

    name: str = "Run Tests"
    description: str = (
        "Runs the test suite in a local repository directory. "
        "Input format: 'CLONE_PATH|||TEST_COMMAND' "
        "Example: '/tmp/repo|||pytest' or '/tmp/repo|||npm test -- --watchAll=false' "
        "Returns: 'PASSED' or 'FAILED' followed by the full test output."
    )

    def _run(self, tool_input: str) -> str:
        clone_path, test_command = tool_input.split("|||", 1)
        try:
            result = subprocess.run(
                test_command.strip(),
                cwd=clone_path.strip(),
                capture_output=True,
                text=True,
                timeout=120,
                shell=True,
            )
        except subprocess.TimeoutExpired:
            return "FAILED\n\nERROR: Test command timed out after 120 seconds."
        except FileNotFoundError as e:
            return f"FAILED\n\nERROR: Test command not found — {e}"

        status = "PASSED" if result.returncode == 0 else "FAILED"
        output = (result.stdout + result.stderr)[:4000]
        return f"{status}\n\n{output}"
