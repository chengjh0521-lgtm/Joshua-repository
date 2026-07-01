from __future__ import annotations

from pydantic import BaseModel

from agents.common import section
from services.deepseek_client import DeepSeekClient


class OriginalityReport(BaseModel):
    passed: bool
    report: str


class OriginalityGuardAgent:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def check(self, chapter: str, originality_rules: str, story_bible: str, trope_library: str) -> OriginalityReport:
        prompt = self.client.render_prompt(
            "originality_check.md",
            chapter=chapter,
            originality_rules=originality_rules,
            story_bible=story_bible,
            trope_library=trope_library,
        )
        result = self.client.chat(prompt, system="你是原创性风控编辑。严查可识别借鉴，但允许抽象类型共性。", temperature=0.2, max_tokens=3000)
        pass_text = (section(result, "PASS") or "").upper()
        report = section(result, "RISK_REPORT") or result
        return OriginalityReport(passed=pass_text.startswith("YES"), report=report)
