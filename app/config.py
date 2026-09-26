import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Settings:
    mongo_uri: str = field(default="", repr=False)
    mongo_seed_uri: str = field(default="", repr=False)
    linear_token: str = field(default="", repr=False)
    mcp_token: str = field(default="", repr=False)
    trueforge_token: str = field(default="", repr=False)
    linear_team_id: str = ""
    issue_id: str = ""
    trueforge_url: str = "http://127.0.0.1:8790"
    model_name: str = ""
    azure_api_key: str = field(default="", repr=False)
    azure_endpoint: str = ""
    azure_llm_model: str = ""
    openai_api_key: str = field(default="", repr=False)
    openai_fallback_enabled: bool = True
    openai_fallback_model: str = ""
    agent_name: str = "roaming-charge-resolver"
    state_path: Path = ROOT / ".state" / "resolver.sqlite"

    @classmethod
    def load(cls):
        load_dotenv(ROOT / ".env")
        value = cls(
            mongo_uri=(
                os.getenv("MONGODB_URI")
                or os.getenv("MONGO_URI")
                or os.getenv("MONGODB_SEED_URI", "")
            ),
            mongo_seed_uri=os.getenv("MONGODB_SEED_URI", ""),
            linear_token=os.getenv("LINEAR_API_TOKEN", ""),
            mcp_token=os.getenv("MCP_AUTH_TOKEN", ""),
            trueforge_token=os.getenv("TRUEFORGE_BEARER_TOKEN", ""),
            linear_team_id=os.getenv("LINEAR_TEAM_ID", ""),
            issue_id=os.getenv("DEMO_LINEAR_ISSUE_ID", ""),
            trueforge_url=os.getenv("TRUEFORGE_BASE_URL", "http://127.0.0.1:8790"),
            model_name=os.getenv("TRUEFORGE_MODEL_NAME", ""),
            azure_api_key=os.getenv("AZURE_API_KEY", ""),
            azure_endpoint=os.getenv("AZURE_ENDPOINT", ""),
            azure_llm_model=os.getenv("AZURE_LLM_MODEL", ""),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_fallback_enabled=os.getenv(
                "OPENAI_FALLBACK_ENABLED", "true"
            ).lower()
            not in {"0", "false", "no"},
            openai_fallback_model=os.getenv("OPENAI_FALLBACK_MODEL", ""),
        )
        if urlparse(value.trueforge_url).hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("TrueForge must run on localhost for this prototype")
        return value

    @property
    def azure_openai_base_url(self):
        """Translate a Foundry project endpoint to its OpenAI v1 inference endpoint."""
        if not self.azure_endpoint:
            return ""
        endpoint = urlparse(self.azure_endpoint)
        if endpoint.scheme != "https" or not endpoint.hostname:
            raise ValueError("AZURE_ENDPOINT must be an absolute HTTPS URL")
        if not endpoint.hostname.endswith((".services.ai.azure.com", ".openai.azure.com")):
            raise ValueError("AZURE_ENDPOINT must be an Azure Foundry/OpenAI endpoint")
        if endpoint.path.rstrip("/").endswith("/openai/v1"):
            return self.azure_endpoint.rstrip("/")
        return f"{endpoint.scheme}://{endpoint.netloc}/openai/v1"

    @property
    def resolved_model_name(self):
        if self.azure_endpoint and self.azure_llm_model:
            return "openai/" + self.azure_llm_model
        return self.model_name or "openai/gpt-5-4-mini"

    @property
    def resolved_fallback_model(self):
        return (
            self.openai_fallback_model
            or self.azure_llm_model
            or self.model_name.removeprefix("openai/")
            or "gpt-6-luna"
        )

    @property
    def openai_fallback_ready(self):
        return self.openai_fallback_enabled and bool(self.openai_api_key)

    def require(self, *names):
        missing = [name for name in names if not getattr(self, name)]
        if missing:
            raise ValueError("Missing configuration: " + ", ".join(missing))
