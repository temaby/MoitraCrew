# MoitraCrew — AI Development Team

An AI-powered development team built on [CrewAI](https://github.com/joaomdmoura/crewAI) and Google Gemini. Given a task and a GitHub repository, the team analyzes the codebase, plans the feature, writes code, reviews it, runs tests, and opens a Pull Request — autonomously.

## Team

| Role | Model | Responsibilities |
|---|---|---|
| **Product Owner** | Gemini 2.5 Flash Lite | Translates ideas into User Stories with Acceptance Criteria, creates GitHub Issues |
| **Architect** | Gemini 2.5 Flash | Analyzes repository, designs technical specification, performs code review |
| **Senior Developer** | Gemini 2.5 Flash | Implements features, fixes code based on test failures and review feedback |
| **QA Engineer** | Gemini 2.5 Flash Lite | Writes test files, creates test plans |

## Modes

### Mode 1 — New project
Generates User Stories, architecture design, implementation, and test plan. Outputs to markdown files. No GitHub write-back.

### Mode 2 — Existing repository
Full development cycle with GitHub integration:

```
analyze repo → user stories → create issue → design architecture
    → implement feature → code review → write tests → run tests
    → fix if failed (up to 3 attempts) → commit + push + open PR
```

Sub-modes:
- **Full run** — runs the entire cycle from scratch
- **Dev only** — skips planning, reuses outputs from the previous run (useful when debugging the implementation step)

## Setup

**Requirements:** Python 3.11+

```bash
# Install dependencies
python -m pip install crewai "crewai[google-genai]" crewai-tools python-dotenv PyGithub

# Configure environment
cp .env.example .env
# Edit .env and set GEMINI_API_KEY (and GITHUB_TOKEN for mode 2)
```

Get a free Gemini API key at https://aistudio.google.com/apikey

## Usage

```bash
cd src/moitracrew
python main.py
```

Follow the prompts:
1. Select mode (1 = new project, 2 = existing repository)
2. Enter your idea or task description
3. For mode 2: provide the GitHub repository URL and choose full/dev-only run

## Output files

All outputs are saved to `src/moitracrew/output/`:

| File | Contents |
|---|---|
| `00_repo_analysis.md` | Repository analysis — tech stack, structure, conventions |
| `01_user_stories.md` | User Stories with Acceptance Criteria |
| `02_architecture.md` | Technical specification — files, models, API contract |
| `03_implementation.md` | List of files written by the Developer |
| `03b_code_review.md` | Architect's code review result (APPROVED / CHANGES_REQUESTED) |
| `04_test_files.md` | List of test files written by QA |
| `05_github_issue.md` | Created GitHub Issue URL and number |
| `06_pull_request.md` | Created Pull Request URL |
| `.last_run.json` | Saved planning state for dev-only reruns |

## Project structure

```
src/moitracrew/
  main.py                   # Entry point — interactive menu
  crew.py                   # Agent definitions and sub-crew builders
  flow.py                   # MoitraFlow — orchestrates the full development cycle
  config/
    agents.yaml             # Agent roles, goals, backstories
    tasks.yaml              # Task descriptions and expected outputs
  tools/
    github_tools.py         # CloneRepoTool — shallow-clones repositories
    github_write_tools.py   # CreateIssueTool, CreateBranchTool, CommitAndPushTool, CreatePRTool
    test_tools.py           # RunTestsTool — runs test suite in cloned repo
  output/                   # Generated files (gitignored)
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Always | Google AI Studio API key |
| `GITHUB_TOKEN` | Mode 2 only | GitHub personal access token with repo scope |
