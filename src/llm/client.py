"""Thin wrapper around Microsoft Foundry's unified chat completions API.

Using the azure-ai-inference SDK means the SAME code works whether the
deployed model is GPT-5.5, DeepSeek-R1, Llama, Mistral, or Claude on Foundry —
you only change FOUNDRY_MODEL_DEPLOYMENT in .env, no code changes.

If you hit deprecation warnings on azure-ai-inference in the future, check
https://learn.microsoft.com/azure/ai-foundry for the current recommended SDK —
Microsoft has been known to shift supported packages. This wrapper isolates
that choice to one file so swapping it out later is a one-file change.
"""
import json
from typing import Optional
from src.config import FoundryConfig
from openai import AzureOpenAI

class FoundryLLMClient:
    def __init__(self, config: Optional[FoundryConfig] = None):
        self.config = config or FoundryConfig.from_env()

        endpoint = self.config.endpoint
        subscription_key = self.config.api_key
        api_version = self.config.api_version
        self.deployment = self.config.model_deployment

        self._client = AzureOpenAI(api_version=api_version,azure_endpoint=endpoint,api_key=subscription_key)
    
    def chat(self,user_prompt: str,system_prompt: str = "You are a helpful assistant.",temperature: float = 0.3,max_tokens: int = 16384,) -> str:
        """Send a single-turn chat request, return the text response."""
        response = self._client.chat.completions.create(
            messages=[
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": user_prompt,
        }],
        max_completion_tokens=max_tokens,
        model=self.deployment)

        return response.choices[0].message.content

    def chat_json(self,user_prompt: str,system_prompt: str,max_tokens: int = 16384) -> dict:
        """Send a chat request expecting a strict JSON object back.

        Raises ValueError if the model didn't return valid JSON, after one
        retry with a stricter reminder appended to the prompt.
        """
        strict_system = (system_prompt + "\n\nRespond with ONLY a valid JSON object. No markdown fences, no preamble, no explanation — just the raw JSON.")

        for attempt in range(2):
            raw = self.chat(user_prompt, strict_system, max_tokens)
            cleaned = raw.strip()

            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`")
                if cleaned.lower().startswith("json"):
                    cleaned = cleaned[4:].strip()
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                if attempt == 0:
                    user_prompt = (user_prompt + "\n\nReminder: output ONLY valid JSON, nothing else." )
                    continue
                raise ValueError(f"Model did not return valid JSON after retry. Got:\n{raw}")
