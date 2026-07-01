from __future__ import annotations

from pydantic import BaseModel

from agents.common import section
from services.deepseek_client import DeepSeekClient
from services.memory_store import NovelMemory


class SlowReaderReport(BaseModel):
    passed: bool
    report: str


class SlowReader:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def read(self, memory: NovelMemory, chapter_number: int, chapter: str) -> SlowReaderReport:
        prompt = self.client.render_prompt(
            "slow_reader.md",
            chapter_number=chapter_number,
            chapter=chapter,
            chapter_summaries=memory.chapter_summaries,
            slow_reader=memory.slow_reader,
        )
        result = self.client.chat(
            prompt,
            system="你是普通网文读者，不是编辑。只反馈连续阅读体验。",
            temperature=0.25,
            max_tokens=3000,
        )
        verdict = (section(result, "VERDICT") or "").upper()
        report = section(result, "REPORT") or result
        return SlowReaderReport(passed=verdict.startswith("PASS"), report=report)
