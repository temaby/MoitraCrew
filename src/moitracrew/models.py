"""Pydantic output models for structured task results."""

from typing import Literal
from pydantic import BaseModel


class ReviewResult(BaseModel):
    """Output of the code_review task."""
    status: Literal["APPROVED", "CHANGES_REQUESTED"]
    issues: list[str] = []


class IssueResult(BaseModel):
    """Output of the create_github_issue task."""
    issue_number: int
    issue_url: str
