"""Stage 1b: pull a candidate's public GitHub repos into GithubProject objects.

Uses the public GitHub REST API. Unauthenticated requests are free and allowed
at 60 requests/hour; set GITHUB_TOKEN in .env to raise that to 5000/hour.
"""
import requests

from src.config import GITHUB_TOKEN
from src.models.schemas import GithubProject

GITHUB_API_BASE = "https://api.github.com"

def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def fetch_github_projects(username: str, max_repos: int = 15, min_stars: int = 0) -> list[GithubProject]:
    """Fetch a user's public, non-fork repos, sorted by most recently pushed."""
    url = f"{GITHUB_API_BASE}/users/{username}/repos"
    params = {"per_page": 100, "sort": "pushed", "type": "owner"}
    resp = requests.get(url, headers=_headers(), params=params, timeout=15)
    if resp.status_code == 403 and resp.headers.get("x-ratelimit-remaining") == "0":
        raise RuntimeError(
            "GitHub API rate limit exceeded (60 requests/hour for unauthenticated calls). "
            "Set GITHUB_TOKEN in .env to raise this to 5000/hour — create one at "
            "https://github.com/settings/tokens (no special scopes needed for public data)."
        )
    resp.raise_for_status()
    repos = resp.json()

    projects = []
    for repo in repos:
        if repo.get("fork"):
            continue
        if repo.get("stargazers_count", 0) < min_stars:
            continue
        languages = _fetch_languages(username, repo["name"])
        projects.append(
            GithubProject(
                name=repo["name"],
                description=repo.get("description"),
                languages=languages,
                stars=repo.get("stargazers_count", 0),
                url=repo.get("html_url", ""),
            )
        )
        if len(projects) >= max_repos:
            break
    return projects


def _fetch_languages(username: str, repo_name: str) -> list[str]:
    url = f"{GITHUB_API_BASE}/repos/{username}/{repo_name}/languages"
    resp = requests.get(url, headers=_headers(), timeout=15)
    if resp.status_code != 200:
        return []
    return list(resp.json().keys())
