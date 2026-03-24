#!/usr/bin/env python3
"""
MoitraCrew — AI development team entry point.

Usage:
    python src/moitracrew/main.py
"""
import os
import shutil
import sys
from pathlib import Path

# Load .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parents[2] / ".env")
except ImportError:
    pass

from crew import MoitraCrew
from tools.github_tools import get_last_clone_path


OUTPUT_DIR = Path(__file__).parents[2] / "output"

NEW_OUTPUT_FILES = [
    "01_user_stories.md",
    "02_architecture.md",
    "03_implementation.md",
    "04_test_plan.md",
]


def _print_separator(title: str = "") -> None:
    print(f"\n{'=' * 60}")
    if title:
        print(title)
        print("=" * 60)


def _print_results(files: list) -> None:
    _print_separator("Results saved to:")
    for filename in files:
        path = OUTPUT_DIR / filename
        if path.exists():
            print(f"  {path}")
    print("=" * 60)


def run_new(user_idea: str, tech_stack_hint: str) -> None:
    """Run the crew in new project mode (no GitHub write-back)."""
    os.chdir(Path(__file__).parent)
    OUTPUT_DIR.mkdir(exist_ok=True)

    _print_separator(f"New project: {user_idea}")

    inputs = {
        "user_idea": user_idea,
        "tech_stack_hint": tech_stack_hint,
        "repo_context": "",
        "repo_url": "",
    }

    MoitraCrew().crew_new().kickoff(inputs=inputs)
    _print_results(NEW_OUTPUT_FILES)


def run_existing(user_idea: str, repo_url: str, skip_planning: bool = False) -> None:
    """Run the full Flow for an existing repository — writes code, runs tests, creates PR."""
    if not os.getenv("GITHUB_TOKEN"):
        print("ERROR: GITHUB_TOKEN is required in .env for existing repository mode.")
        sys.exit(1)

    os.chdir(Path(__file__).parent)
    OUTPUT_DIR.mkdir(exist_ok=True)

    label = "dev-only (reusing planning outputs)" if skip_planning else repo_url
    _print_separator(f"Existing repo: {label}\nTask: {user_idea}")

    from flow import MoitraFlow

    flow = MoitraFlow()
    flow.state.user_idea = user_idea
    flow.state.repo_url = repo_url
    flow.state.skip_planning = skip_planning

    try:
        flow.kickoff()
    finally:
        # Clean up the cloned repository temp directory
        clone_path = get_last_clone_path()
        if clone_path and Path(clone_path).exists():
            shutil.rmtree(clone_path, ignore_errors=True)


def main() -> None:
    print("\nMoitraCrew — AI Development Team")
    print("-" * 36)
    print("Select mode:")
    print("  1. New project")
    print("  2. Existing repository")

    mode = input("\n> ").strip()

    if mode == "1":
        user_idea = input("\nDescribe your idea: ").strip()
        if not user_idea:
            user_idea = "Personal expense tracking dashboard with charts"

        tech_stack = input("Tech stack (leave empty — architect decides): ").strip()
        run_new(user_idea, tech_stack)

    elif mode == "2":
        repo_url = input("\nGitHub repository URL: ").strip()
        if not repo_url:
            print("ERROR: Repository URL is required.")
            sys.exit(1)

        user_idea = input("What needs to be done (feature or bug fix): ").strip()
        if not user_idea:
            print("ERROR: Task description is required.")
            sys.exit(1)

        print("\nRun mode:")
        print("  f. Full run  — analyze repo, plan, implement, test, PR")
        print("  d. Dev only  — skip planning, reuse outputs from last run (faster for debugging)")
        run_mode = input("\n> ").strip().lower()
        skip_planning = run_mode == "d"

        run_existing(user_idea, repo_url, skip_planning=skip_planning)

    else:
        print("Invalid choice. Please enter 1 or 2.")
        sys.exit(1)


if __name__ == "__main__":
    main()
