"""Tailor a LaTeX resume to a job description using the parsed candidate profile."""
from pathlib import Path
import sys
import re
from uuid import UUID

from src.llm.client import FoundryLLMClient
from src.models.schemas import CandidateProfile
from src.models.tailoring import ResumeTailoringResult
import json
from typing import Dict
import requests
from datetime import date
from src.config import NOTION_API_TOKEN, NOTION_DATABASE_ID

TAILORING_SYSTEM_PROMPT = """You are a senior resume tailoring assistant.
Given a raw job description, a structured candidate profile (JSON), and a reference LaTeX
resume source, produce a FULLY TAILORED resume in LaTeX with ALL changes actually implemented.

IMPORTANT:
- The candidate profile JSON contains ALL the candidate data (experience, projects, skills, education).
- Do NOT extract or re-parse data from the base_resume.tex file.
- Use base_resume.tex ONLY as a formatting and structure reference to understand LaTeX conventions and personal information.
- Generate the new resume content using ONLY the data from the candidate profile JSON for skills, experience, and projects.

Sections to PRESERVE as-is (copy directly from base_resume.tex):
- The entire heading/contact block with name, phone, email, location, GitHub URL, LinkedIn URL
- The Education section
- Within the skillGroup, preserve the values in the sections "Programming Languages", "Cloud & Databases" and "Web and Systems". you can add content in these sections, but do not remove any of the existing content.

Sections to MODIFY IN THE tailored_tex OUTPUT (do not suggest; IMPLEMENT changes):
- Technical Skills: In the "Technical Skills" section of the SkillGroup, ACTUALLY REMOVE skills that don't match the job description. REORDER remaining skills by job relevance. Draw skills from candidate profile's skillGroup. Note: ensure that you remove the skills only if you think they are completely unrelevant to the JD, otherwise don't.
- Work Experience: ACTUALLY FILTER to keep only 2 out of the 3 work most relevant entries from the candidate profile's experience list. Remove irrelevant entries entirely. Keep all the 3 entries given only if you feel they are all relevant to this resume more than the projects listed, otherwise have only 2 work experience and 3 projects instead of 3 work experience and 2 projects.
- Projects: ACTUALLY FILTER to keep only 3 most relevant entries from the candidate profile's resume_projects list. Remove irrelevant projects entirely.
- Bullet Points: For retained experience and project entries, REWRITE their bullet points to emphasize keywords and accomplishments that match the job description. This is very important for ATS compatibility and relevance. Use the job description language and terminology to guide the rewriting.
- Bullet Point Count: For each retained experience or project, keep a maximum of 3 bullet points for the most relevant project and for the rest only 2 bullet points. If the original entry has more than 3, select the most relevant ones to the job description and rewrite them to highlight keywords and accomplishments.

Implementation Requirements:
- Preserve ALL personal information from the heading (name, contact details, GitHub URL, LinkedIn URL).
- Keep the output faithful to the candidate's actual background; do not invent experience.
- FILTER skills, experience, and projects directly in tailored_tex—do not include them if they don't match the job description.
- Maximum of 5 total entries across work experience and projects combined (e.g., 2 experiences + 3 projects, or 3 experiences + 2 projects).
- Reorder skills to put the most job-relevant at the top.
- For each retained entry (experience or project), rewrite bullet points to highlight keywords, tools, and accomplishments that align with the job description.
- Match tone and terminology from the job description to improve ATS compatibility and relevance.
- Preserve the LaTeX section structure and formatting pattern from the reference resume.
- Do not redesign the resume layout or invent new sections. Only revise content inside the skills, experience, and projects sections.
- Preserve the original LaTeX command style (resumeSubheading, resumeItem, etc.) for consistency.
- If a significantly better-fit project exists in the GitHub portfolio (github_projects) that should replace a current project, mention it in better_fit_project_suggestions.

Output JSON Schema (MUST include ALL these fields):
{
  "tailored_tex": "complete updated LaTeX document with ALL changes implemented",
  "suggestions_to_add": [],
  "suggestions_to_remove": [],
  "selected_experience_titles": ["title of each experience entry kept in resume"],
  "selected_project_titles": ["title of each project kept in resume"],
  "excluded_experience_titles": ["title of each experience entry removed"],
  "excluded_project_titles": ["title of each project removed"],
  "skills_keywords_used": ["keyword from job description that was emphasized in skills section"],
  "skills_keywords_removed": ["skill keyword that was filtered out as not matching job"],
  "better_fit_project_suggestions": [{"source": "github", "name": "project name", "reason": "why this would be a better fit than what was kept", "replace_with": "current project being replaced", "keep_in_resume": false}],
  "fit_summary": "brief explanation of the filtering and rewriting decisions"
}
"""


SKILL_EXTRACTION_SYSTEM_PROMPT = """You are a compact skill-extraction assistant.
Given a single job description, extract three groups of items found in the text:
1) softskills (e.g. "communication", "teamwork") — return the exact words as they appear in the JD but with the first letter of each word capitalized;
2) technical_skills (e.g. "python", "react") — return the exact words as they appear in the JD but with the first letter of each word capitalized;
3) development_practices (e.g. "agile methodologies", "test-driven development") — summarize these into short resume-friendly phrases (no sentences) and capitalize first letters.

Output requirements:
- Return valid JSON ONLY with three keys: `softskills`, `technical_skills`, `development_practices`.
- Each value must be a single comma-separated string (no surrounding lists), with items capitalized (first letter of each word uppercase) and no trailing commas or punctuation.
- Do not add any commentary or extra keys.

Example output (exact JSON format):
{"softskills": "Teamwork, Communication", "technical_skills": "Python, React, Docker", "development_practices": "Test-Driven Development, Continuous Integration"}
"""


def _read_text(file_path: str) -> str:
    return Path(file_path).read_text(encoding="utf-8")


def _normalize_notion_database_id(raw_database_id: str) -> str:
    """Accept a raw UUID, hyphenless UUID, or pasted Notion URL and return a valid database id."""
    if not raw_database_id:
        return ""

    candidate = raw_database_id.strip()
    match = re.search(r"([0-9a-fA-F]{32}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", candidate)
    if match:
        try:
            return str(UUID(match.group(1)))
        except ValueError:
            return match.group(1)

    return candidate


def _chunk_text(text: str, max_chars: int = 1800) -> list[str]:
    """Split text into chunks that stay under Notion rich_text limits."""
    cleaned = text.strip()
    if not cleaned:
        return [""]

    chunks = []
    remaining = cleaned
    while len(remaining) > max_chars:
        split_at = remaining.rfind("\n\n", 0, max_chars)
        if split_at == -1:
            split_at = remaining.rfind("\n", 0, max_chars)
        if split_at == -1:
            split_at = remaining.rfind(" ", 0, max_chars)
        if split_at == -1 or split_at < max_chars // 2:
            split_at = max_chars

        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].lstrip()

    if remaining:
        chunks.append(remaining)

    return chunks


def tailor_resume(
    job_description: str,
    profile: CandidateProfile,
    resume_tex_path: str,
    llm_client: FoundryLLMClient,
) -> ResumeTailoringResult:
    """Generate a tailored resume draft and structured recommendations."""
    resume_tex = _read_text(resume_tex_path)
    # First, extract skills from the job description so the tailoring step can rely on
    # a normalized, copy-paste-friendly list of skills and practices.
    def _extract_skills(jd: str, client: FoundryLLMClient) -> Dict[str, str]:
        jd_prompt = "Job description:\n\n" + jd + "\n\n"
        result = client.chat_json(user_prompt=jd_prompt, system_prompt=SKILL_EXTRACTION_SYSTEM_PROMPT)
        # result should be a dict with the three comma-separated strings
        return result

    extracted = _extract_skills(job_description, llm_client)

    user_prompt = (
        "Job description:\n\n"
        f"{job_description}\n\n"
        "Extracted skills from job description (softskills, technical_skills, development_practices):\n\n"
        f"{json.dumps(extracted, ensure_ascii=False)}\n\n"
        "Candidate profile JSON:\n\n"
        f"{profile.model_dump_json(indent=2)}\n\n"
        "Current resume.tex:\n\n"
        f"{resume_tex}\n"
    )

    data = llm_client.chat_json(
        user_prompt=user_prompt,
        system_prompt=TAILORING_SYSTEM_PROMPT,
    )

    result = ResumeTailoringResult(**data)

    # Try to extract organization and role from the job description to populate Notion.
    def _extract_org_role(jd: str, client: FoundryLLMClient) -> Dict[str, str]:
        system = (
            "You are a concise extractor. Given a job description, return only valid JSON with two keys:"
            " \"organization\" and \"role\". If the information is not present, use empty strings."
            " Examples: {\"organization\": \"Acme Corp\", \"role\": \"Software Engineer\"}"
        )
        jd_prompt = "Job description:\n\n" + jd + "\n\n"
        try:
            parsed = client.chat_json(user_prompt=jd_prompt, system_prompt=system)
            if isinstance(parsed, dict):
                return {"organization": parsed.get("organization", ""), "role": parsed.get("role", "")}
        except Exception:
            pass
        return {"organization": "", "role": ""}

    def _push_to_notion(organization: str, role: str, jd_text: str) -> Dict:
        if not NOTION_API_TOKEN or not NOTION_DATABASE_ID:
            return {"ok": False, "reason": "NOTION_API_TOKEN or NOTION_DATABASE_ID not set"}

        database_id = _normalize_notion_database_id(NOTION_DATABASE_ID)
        if not database_id:
            return {"ok": False, "reason": "NOTION_DATABASE_ID is empty or invalid"}

        url = "https://api.notion.com/v1/pages"
        headers = {
            "Authorization": f"Bearer {NOTION_API_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

        today_str = date.today().isoformat()

        jd_blocks = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "Job Description"}}]
                },
            }
        ] + [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}],
                },
            }
            for chunk in _chunk_text(jd_text)
        ]

        payload = {
            "parent": {"database_id": database_id},
            "properties": {
                "Organization": {"title": [{"text": {"content": organization or ""}}]},
                "Role": {"rich_text": [{"text": {"content": role or ""}}]},
                "Status": {"status": {"name": "Applied"}},
                "Date": {"date": {"start": today_str}},
                "JD": {
                    "rich_text": [
                        {"type": "text", "text": {"content": chunk}}
                        for chunk in _chunk_text(jd_text)
                    ]
                },
            },
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            if not resp.ok:
                return {"ok": False, "status_code": resp.status_code, "text": resp.text}

            page_id = resp.json().get("id")
            if not page_id:
                return {"ok": False, "reason": "Notion page created but response did not include a page id"}

            append_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
            append_payload = {"children": jd_blocks}
            append_resp = requests.patch(append_url, headers=headers, json=append_payload, timeout=15)
            if not append_resp.ok:
                return {
                    "ok": False,
                    "status_code": append_resp.status_code,
                    "text": append_resp.text,
                    "page_id": page_id,
                }

            return {"ok": True, "page_id": page_id}
        except Exception as e:
            return {"ok": False, "reason": str(e)}

    org_role = _extract_org_role(job_description, llm_client)
    notion_resp = _push_to_notion(org_role.get("organization", ""), org_role.get("role", ""), job_description)

    if notion_resp.get("ok"):
        print(
            "Notion application row created: "
            f"organization={org_role.get('organization', '')!r}, "
            f"role={org_role.get('role', '')!r}, "
            f"date={date.today().isoformat()}, "
            f"status='Applied'",
            file=sys.stderr,
        )
    else:
        error_detail = notion_resp.get("reason") or notion_resp.get("text") or "unknown error"
        status_code = notion_resp.get("status_code")
        prefix = f"Notion application row failed"
        if status_code is not None:
            prefix += f" (HTTP {status_code})"
        print(
            f"{prefix}: {error_detail}",
            file=sys.stderr,
        )

    return result