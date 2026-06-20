"""Parse a real resume file using your configured Foundry model, and print the structured profile.

Usage:
    python scripts/parse_resume.py /path/to/resume.pdf/.tex/.docx/.txt
    python scripts/parse_resume.py /path/to/resume.pdf/.tex/.docx/.txt --github yourusername
    python scripts/parse_resume.py /path/to/resume.pdf/.tex/.docx/.txt --jsonl_path ./profile.jsonl
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.ingestion.github_fetcher import fetch_github_projects
from src.ingestion.resume_parser import parse_resume
from src.llm.client import FoundryLLMClient
from src.models.schemas import CandidateProfile


def append_profile_jsonl(profile: CandidateProfile, jsonl_path: str) -> None:
    """Append one CandidateProfile JSON object as a JSONL row."""
    path = Path(jsonl_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as file_handle:
        file_handle.write(profile.model_dump_json())
        file_handle.write("\n")

def main():
    parser = argparse.ArgumentParser(description="Parse a resume into a structured profile.")
    parser.add_argument("--resume_path", help="Path to .pdf, .docx, or .txt resume", type=str, default="./base_resume.tex", required=False)
    parser.add_argument("--github", help="GitHub username to also pull projects from", default="Sujith013", type=str)
    parser.add_argument(
        "--jsonl_path",
        help="Path to a JSONL file where parsed profiles will be appended",
        type=str,
        default="./profile.jsonl",
    )
    args = parser.parse_args()

    print(f"Connecting to Foundry and parsing {args.resume_path} ...")
    llm = FoundryLLMClient()
    profile = parse_resume(args.resume_path, llm)

    if args.github:
        print(f"Fetching GitHub projects for {args.github} ...")
        profile.github_projects = fetch_github_projects(args.github)

    print("\n--- Structured candidate profile ---\n")
    print(json.dumps(profile.model_dump(), indent=2))

    append_profile_jsonl(profile, args.jsonl_path)

if __name__ == "__main__":
    main()
