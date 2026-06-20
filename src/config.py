"""Central configuration, loaded from environment variables / .env file."""
import os
from dataclasses import dataclass
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

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")
NOTION_API_TOKEN = os.environ.get("NOTION_API_TOKEN", "")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "")