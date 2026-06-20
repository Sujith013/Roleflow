"""Structured output for resume tailoring against a job description."""
from typing import Optional

from pydantic import BaseModel, Field


class ProjectSuggestion(BaseModel):
    source: str
    name: str
    reason: str
    replace_with: Optional[str] = None
    keep_in_resume: bool = False


class ResumeTailoringDraft(BaseModel):
    skills_section_tex: str = ""
    work_experience_section_tex: str = ""
    projects_section_tex: str = ""
    suggestions_to_add: list[str] = Field(default_factory=list)
    suggestions_to_remove: list[str] = Field(default_factory=list)
    selected_experience_titles: list[str] = Field(default_factory=list)
    selected_project_titles: list[str] = Field(default_factory=list)
    excluded_experience_titles: list[str] = Field(default_factory=list)
    excluded_project_titles: list[str] = Field(default_factory=list)
    skills_keywords_used: list[str] = Field(default_factory=list)
    skills_keywords_removed: list[str] = Field(default_factory=list)
    better_fit_project_suggestions: list[ProjectSuggestion] = Field(default_factory=list)
    fit_summary: str = ""


class ResumeTailoringResult(ResumeTailoringDraft):
    tailored_tex: str