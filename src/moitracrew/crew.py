"""MoitraCrew — AI development team crew and sub-crew definitions."""

import os
from crewai import Agent, Crew, Process, LLM, Task
from crewai.project import CrewBase, agent, task
from crewai_tools import DirectoryReadTool, FileReadTool, FileWriterTool

from models import ReviewResult, IssueResult
from tools.github_tools import CloneRepoTool
from tools.github_write_tools import (
    CreateIssueTool,
    CreateBranchTool,
    CommitAndPushTool,
    CreatePRTool,
)
from tools.test_tools import RunTestsTool


_MODEL_LITE = "gemini-3-flash-lite-preview"   # structured text, low reasoning demand
_MODEL_FLASH = "gemini-3-flash-preview"       # code generation and analysis


def make_llm(model: str = _MODEL_LITE) -> LLM:
    return LLM(
        model=f"gemini/{model}",
        api_key=os.environ["GEMINI_API_KEY"],
    )


@CrewBase
class MoitraCrew:
    """AI Development Team — Product Owner, Architect, Senior Developer, QA Engineer."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # ── Agents ───────────────────────────────────────────────────────────────

    @agent
    def product_owner(self) -> Agent:
        return Agent(
            config=self.agents_config["product_owner"],
            llm=make_llm(_MODEL_LITE),
            verbose=True,
            max_iter=5,
        )

    @agent
    def architect(self) -> Agent:
        return Agent(
            config=self.agents_config["architect"],
            llm=make_llm(_MODEL_FLASH),
            verbose=True,
            max_iter=8,
        )

    @agent
    def senior_developer(self) -> Agent:
        return Agent(
            config=self.agents_config["senior_developer"],
            llm=make_llm(_MODEL_FLASH),
            verbose=True,
            max_iter=20,
            planning=True,
            planning_llm=make_llm(_MODEL_LITE),
        )

    @agent
    def qa_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config["qa_engineer"],
            llm=make_llm(_MODEL_LITE),
            verbose=True,
            max_iter=5,
        )

    # ── Tasks ─────────────────────────────────────────────────────────────────

    @task
    def analyze_repository(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_repository"],
            tools=[CloneRepoTool(), DirectoryReadTool(), FileReadTool()],
            output_file="output/00_repo_analysis.md",
        )

    @task
    def create_user_stories(self) -> Task:
        return Task(
            config=self.tasks_config["create_user_stories"],
            output_file="output/01_user_stories.md",
        )

    @task
    def create_github_issue(self) -> Task:
        return Task(
            config=self.tasks_config["create_github_issue"],
            tools=[CreateIssueTool()],
            output_pydantic=IssueResult,
            output_file="output/05_github_issue.md",
        )

    @task
    def design_architecture(self) -> Task:
        return Task(
            config=self.tasks_config["design_architecture"],
            output_file="output/02_architecture.md",
        )

    @task
    def implement_feature(self) -> Task:
        return Task(
            config=self.tasks_config["implement_feature"],
            tools=[CreateBranchTool(), FileWriterTool()],
            output_file="output/03_implementation.md",
        )

    @task
    def fix_implementation(self) -> Task:
        return Task(
            config=self.tasks_config["fix_implementation"],
            tools=[FileReadTool(), FileWriterTool()],
            output_file="output/03_implementation_fix.md",
        )

    @task
    def code_review(self) -> Task:
        return Task(
            config=self.tasks_config["code_review"],
            tools=[DirectoryReadTool(), FileReadTool()],
            output_pydantic=ReviewResult,
            output_file="output/03b_code_review.md",
        )

    @task
    def create_test_files(self) -> Task:
        return Task(
            config=self.tasks_config["create_test_files"],
            tools=[FileWriterTool()],
            output_file="output/04_test_files.md",
        )

    @task
    def create_pull_request(self) -> Task:
        return Task(
            config=self.tasks_config["create_pull_request"],
            tools=[CommitAndPushTool(), CreatePRTool()],
            output_file="output/06_pull_request.md",
        )

    @task
    def create_test_plan(self) -> Task:
        return Task(
            config=self.tasks_config["create_test_plan"],
            output_file="output/04_test_plan.md",
        )

    # ── Sub-crews (used by MoitraFlow) ────────────────────────────────────────

    def planning_crew(self) -> Crew:
        """Analyze repo, write user stories, create GitHub issue, design architecture."""
        return Crew(
            agents=[self.architect(), self.product_owner()],
            tasks=[
                self.analyze_repository(),
                self.create_user_stories(),
                self.create_github_issue(),
                self.design_architecture(),
            ],
            process=Process.sequential,
            verbose=True,
        )

    def dev_crew(self) -> Crew:
        """Implement the feature — writes files to the cloned repo."""
        return Crew(
            agents=[self.senior_developer()],
            tasks=[self.implement_feature()],
            process=Process.sequential,
            verbose=True,
        )

    def fix_crew(self) -> Crew:
        """Fix failing code given test error output."""
        return Crew(
            agents=[self.senior_developer()],
            tasks=[self.fix_implementation()],
            process=Process.sequential,
            verbose=True,
        )

    def review_crew(self) -> Crew:
        """Architect reviews the implementation for security and architecture issues."""
        return Crew(
            agents=[self.architect()],
            tasks=[self.code_review()],
            process=Process.sequential,
            verbose=True,
        )

    def qa_crew(self) -> Crew:
        """Write test files to the cloned repo."""
        return Crew(
            agents=[self.qa_engineer()],
            tasks=[self.create_test_files()],
            process=Process.sequential,
            verbose=True,
        )

    def publish_crew(self) -> Crew:
        """Commit, push, and open a PR."""
        return Crew(
            agents=[self.architect()],
            tasks=[self.create_pull_request()],
            process=Process.sequential,
            verbose=True,
        )

    # ── Standalone crews (no GitHub write-back) ───────────────────────────────

    def crew_new(self) -> Crew:
        """New project mode — architect chooses or follows the provided tech stack."""
        return Crew(
            agents=[
                self.product_owner(),
                self.architect(),
                self.senior_developer(),
                self.qa_engineer(),
            ],
            tasks=[
                self.create_user_stories(),
                self.design_architecture(),
                self.implement_feature(),
                self.create_test_plan(),
            ],
            process=Process.sequential,
            verbose=True,
        )
