from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("NOVEL_AGENT_DATA_DIR", PROJECT_ROOT / "data"))
OUTPUT_DIR = Path(os.getenv("NOVEL_AGENT_OUTPUT_DIR", PROJECT_ROOT / "output"))
MEMORY_DIR = Path(os.getenv("NOVEL_AGENT_MEMORY_DIR", PROJECT_ROOT / "novel_memory"))


class Settings(BaseModel):
    deepseek_api_key: str = Field(default="")
    deepseek_model: str = Field(default="deepseek-chat")
    deepseek_base_url: str = Field(default="https://api.deepseek.com")
    timeout_seconds: float = Field(default=120.0)

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv(PROJECT_ROOT / ".env")
        return cls(
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
            deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip(),
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip().rstrip("/"),
        )


def get_settings(require_api_key: bool = True) -> Settings:
    settings = Settings.load()
    if require_api_key and not settings.deepseek_api_key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY. Copy .env.example to .env and fill in your key.")
    return settings
