"""Tailor Resume.tex to a job description using the parsed profile and Foundry LLM."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingestion.resume_tailor import tailor_resume
from src.llm.client import FoundryLLMClient
from src.models.schemas import CandidateProfile


def load_job_description(file_path: str) -> str:
    return Path(file_path).read_text(encoding="utf-8")


def load_profile(profile_path: str) -> CandidateProfile:
    path = Path(profile_path)
    raw = path.read_text(encoding="utf-8")

    if path.suffix.lower() == ".jsonl":
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if not lines:
            raise ValueError(f"No JSON objects found in {profile_path}")
        profile_data = json.loads(lines[-1])
        return CandidateProfile(**profile_data)

    profile_data = json.loads(raw)
    return CandidateProfile(**profile_data)


def main():
    parser = argparse.ArgumentParser(description="Tailor a resume to a job description.")
    parser.add_argument("--job_description_file", default="./job_description.txt", type=str, help="Path to a text file containing the job description")
    parser.add_argument("--resume_path", type=str, default="./base_resume.tex", help="Path to the current resume.tex file")
    parser.add_argument("--profile_jsonl", type=str, default="./profile.jsonl", help="Path to a CandidateProfile JSON or JSONL file")
    parser.add_argument("--output_tex", default="./resume_sujith.tex", type=str, help="Where to write the tailored LaTeX draft")
    args = parser.parse_args()

    llm = FoundryLLMClient()

    profile = load_profile(args.profile_jsonl)
    job_description = load_job_description(args.job_description_file)
    result = tailor_resume(job_description, profile, args.resume_path, llm)

    Path(args.output_tex).write_text(result.tailored_tex, encoding="utf-8")

    print(json.dumps(result.model_dump(), indent=2))


if __name__ == "__main__":
    main()