from __future__ import annotations

from pydantic import BaseModel

from agents.common import section
from services.deepseek_client import DeepSeekClient
from services.memory_store import NovelMemory


class ContinuityReport(BaseModel):
    passed: bool
    report: str


class ContinuityAgent:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def check(self, memory: NovelMemory, chapter_plan: str, chapter: str) -> ContinuityReport:
        prompt = self.client.render_prompt(
            "continuity_check.md",
            system_rules=memory.system_rules,
            chapter_plan=chapter_plan,
            chapter=chapter,
            story_bible=memory.story_bible,
            outline=memory.outline,
            characters=memory.characters,
            world=memory.world,
            lore_db=memory.lore_db,
            plot_timeline=memory.plot_timeline,
            foreshadowing=memory.foreshadowing,
            chapter_summaries=memory.chapter_summaries,
        )
        result = self.client.chat(
            prompt,
            system="你是小说连续性检查员。只检查，不改写正文。",
            temperature=0.15,
            max_tokens=3500,
        )
        verdict = (section(result, "VERDICT") or "").upper()
        report = section(result, "REPORT") or result
        return ContinuityReport(passed=verdict.startswith("PASS"), report=report)
