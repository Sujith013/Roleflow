"""Stage 1a: turn a resume file (pdf/docx/tex/txt) into a structured CandidateProfile.

Two-step process, deliberately separated so each step is testable on its own:
  1. extract_text()   -- pure text extraction, no LLM, no network, instant to test
  2. structure_resume() -- one LLM call that maps free text -> CandidateProfile
"""
import re
from pathlib import Path

import pdfplumber
from docx import Document

from src.llm.client import FoundryLLMClient
from src.models.schemas import CandidateProfile

STRUCTURING_SYSTEM_PROMPT = """You are a precise resume-parsing engine. Given raw
resume text, extract the candidate's information into the exact JSON schema below.
Do not invent information that isn't present — use null/empty values for missing
fields. Preserve bullet points under each role as separate strings.

The input may be plain text, or it may be LaTeX source (containing commands like
\\section, \\textbf, \\item, \\resumeItem, or other custom macros). If so, ignore
the markup/formatting commands and extract only the underlying semantic content —
e.g. \\textbf{Software Engineer} means the title is "Software Engineer".

Schema:
{
  "name": str,
  "email": str | null,
  "phone": str | null,
  "location": str | null,
  "skillGroup": {
    "programming_languages": [str],
    "technical_skills": [str],
    "web_and_systems": [str],
    "cloud_and_databases": [str],
    "development_practices": [str]
  },
  "experience": [
    {"title": str, "company": str, "start_date": str | null, "end_date": str | null, "location": str | null, "bullets": [str]}
  ],
  "education": [
    {"degree": str, "institution": str, "year": str | null}
  ],
  "resume_projects": [
    {"title": str, "techstack": str, "github_url": str | null, "demo_url": str | null, "paper_url": str | null, "website_url": str | null, "bullets": [str]}
  ]
}
"""


def extract_text(file_path: str) -> str:
    """Extract raw text from a .pdf, .docx, .tex, or .txt resume file."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        text_parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    if suffix == ".docx":
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    if suffix == ".tex":
        raw = path.read_text(encoding="utf-8")
        return _strip_latex_comments(raw)

    if suffix == ".txt":
        return path.read_text(encoding="utf-8")

    raise ValueError(f"Unsupported resume file type: {suffix}. Use .pdf, .docx, .tex, or .txt")


def _strip_latex_comments(tex_source: str) -> str:
    """Remove LaTeX comments (unescaped % to end of line) before sending to the LLM.

    Keeps all actual macros/commands intact -- the LLM is instructed to parse
    around those. This only strips noise that has zero semantic value.
    """
    lines = []
    for line in tex_source.splitlines():
        # Find an unescaped '%' (not preceded by a backslash) and truncate there.
        match = re.search(r"(?<!\\)%", line)
        cleaned = line[: match.start()] if match else line
        lines.append(cleaned)
    return "\n".join(lines)


def structure_resume(resume_text: str, llm_client: FoundryLLMClient) -> CandidateProfile:
    """Use the LLM to map raw resume text onto the CandidateProfile schema."""
    data = llm_client.chat_json(
        user_prompt=f"Resume text:\n\n{resume_text}",
        system_prompt=STRUCTURING_SYSTEM_PROMPT,
    )

    return CandidateProfile(**data)


def parse_resume(file_path: str, llm_client: FoundryLLMClient) -> CandidateProfile:
    """End-to-end: file path -> structured CandidateProfile."""
    text = extract_text(file_path)

    if not text.strip():
        raise ValueError(f"No extractable text found in {file_path} — is it a scanned image PDF?")
    return structure_resume(text, llm_client)
