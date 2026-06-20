"""Structured representation of a candidate, assembled from resume + GitHub
(+ later, LinkedIn export). This is the canonical object every later stage
(matching, tailoring) reads from.
"""
from typing import List, Optional
from pydantic import BaseModel, Field

class Experience(BaseModel):
    title: str
    company: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location: Optional[str] = None
    bullets: list[str] = Field(default_factory=list)


class ResumeProjects(BaseModel):
    title: str
    techstack: str
    github_url: Optional[str] = None
    demo_url: Optional[str] = None
    paper_url: Optional[str] = None
    website_url: Optional[str] = None
    bullets: list[str] = Field(default_factory=list)


class SkillGroup(BaseModel):
    programming_languages: List[str] = Field(default_factory=list)
    technical_skills: List[str] = Field(default_factory=list)
    web_and_systems: List[str] = Field(default_factory=list)
    cloud_and_databases: List[str] = Field(default_factory=list)
    development_practices: List[str] = Field(default_factory=list)


class Education(BaseModel):
    degree: str
    institution: str
    year: Optional[str] = None



class GithubProject(BaseModel):
    name: str
    description: Optional[str] = None
    languages: list[str] = Field(default_factory=list)
    stars: int = 0
    url: str = ""


class CandidateProfile(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    skillGroup: SkillGroup = Field(default_factory=SkillGroup)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    resume_projects: list[ResumeProjects] = Field(default_factory=list)
    github_projects: list[GithubProject] = Field(default_factory=list)