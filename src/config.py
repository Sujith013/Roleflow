"""Central configuration, loaded from environment variables / .env file."""
import os
import re
from dataclasses import dataclass
from uuid import UUID
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class FoundryConfig:
    endpoint: str
    api_key: str
    api_version: str
    model_deployment: str

    @classmethod
    def from_env(cls) -> "FoundryConfig":
        endpoint = os.environ.get("FOUNDRY_ENDPOINT", "")
        api_key = os.environ.get("FOUNDRY_API_KEY", "")
        api_version = os.environ.get("API_VERSION", "2024-12-01-preview")
        model_deployment=os.environ.get("FOUNDRY_MODEL_DEPLOYMENT", "gpt-5.4")

        if not endpoint or not api_key or not api_version or not model_deployment:
            raise RuntimeError(
                "FOUNDRY_ENDPOINT, FOUNDRY_API_KEY, API_VERSION, and FOUNDRY_MODEL_DEPLOYMENT must be set (see .env.example). "
                "Get these from your model deployment in https://ai.azure.com"
            )
        return cls(endpoint=endpoint, api_key=api_key, api_version=api_version, model_deployment= model_deployment)


def _normalize_notion_database_id(raw_database_id: str) -> str:
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

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")
NOTION_API_TOKEN = os.environ.get("NOTION_API_TOKEN", "")
NOTION_DATABASE_ID = _normalize_notion_database_id(os.environ.get("NOTION_DATABASE_ID", ""))