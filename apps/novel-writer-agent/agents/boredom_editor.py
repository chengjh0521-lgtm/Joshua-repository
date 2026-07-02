from __future__ import annotations

from pydantic import BaseModel

from agents.common import section
from services.deepseek_client import DeepSeekClient


class BoredomEditorReport(BaseModel):
    passed: bool
    report: str


class BoredomEditor:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def judge(self, chapter_plan: str, chapter: str) -> BoredomEditorReport:
        prompt = self.client.render_prompt(
            "boredom_editor.md",
            chapter_plan=chapter_plan,
            chapter=chapter,
        )
        result = self.client.chat(
            prompt,
            system="你是小说无聊度编辑。只判断章节是否缺少呼吸，不改写正文。",
            temperature=0.2,
            max_tokens=3000,
        )
        verdict = (section(result, "VERDICT") or "").upper()
        report = section(result, "REPORT") or result
        return BoredomEditorReport(passed=verdict.startswith("PASS"), report=report)
