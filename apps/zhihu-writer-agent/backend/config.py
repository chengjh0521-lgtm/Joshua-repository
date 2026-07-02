from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field
import os


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
DATA_DIR = BASE_DIR / "data"
ARTICLES_DIR = DATA_DIR / "articles"
TXT_OUTPUTS_DIR = PROJECT_DIR / "txt_outputs"
PROMPTS_DIR = BASE_DIR / "prompts"
EDITORIAL_PRINCIPLE_PROMPT = "editorial_principle.md"
PROMPTS_WITH_EDITORIAL_PRINCIPLE = {
    "outline.md",
    "write_article.md",
    "review_article.md",
    "rewrite_article.md",
    "final_check.md",
    "idea_outline.md",
    "idea_write.md",
    "idea_review.md",
    "idea_rewrite.md",
    "idea_final_check.md",
}

load_dotenv(PROJECT_DIR / ".env")


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseModel):
    deepseek_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY"))
    deepseek_base_url: str = Field(
        default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )
    deepseek_model: str = Field(default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
    database_path: Path = DATA_DIR / "zhihu_agent.db"
    articles_dir: Path = ARTICLES_DIR
    txt_outputs_dir: Path = TXT_OUTPUTS_DIR
    zhihu_user_data_dir: Path = DATA_DIR / "playwright_zhihu_profile"
    zhihu_editor_url: str = Field(
        default_factory=lambda: os.getenv("ZHIHU_EDITOR_URL", "https://zhuanlan.zhihu.com/write")
    )
    zhihu_idea_url: str = Field(
        default_factory=lambda: os.getenv("ZHIHU_IDEA_URL", "https://www.zhihu.com")
    )
    zhihu_headless: bool = Field(default_factory=lambda: env_bool("ZHIHU_HEADLESS", False))
    zhihu_draft_wait_seconds: int = Field(
        default_factory=lambda: int(os.getenv("ZHIHU_DRAFT_WAIT_SECONDS", "8"))
    )

settings = Settings()


def ensure_runtime_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    try:
        TXT_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        pass
    settings.zhihu_user_data_dir.mkdir(parents=True, exist_ok=True)


def read_prompt(name: str) -> str:
    prompt_path = PROMPTS_DIR / name
    prompt = prompt_path.read_text(encoding="utf-8")
    if name in PROMPTS_WITH_EDITORIAL_PRINCIPLE:
        principle = (PROMPTS_DIR / EDITORIAL_PRINCIPLE_PROMPT).read_text(encoding="utf-8")
        return principle.rstrip() + "\n\n---\n\n" + prompt
    return prompt
