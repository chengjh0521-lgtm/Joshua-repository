from __future__ import annotations

from pydantic import BaseModel

from agents.common import section
from services.deepseek_client import DeepSeekClient
from services.memory_store import NovelMemory


class MemoryUpdate(BaseModel):
    chapter_summary: str
    characters: str
    plot_timeline: str
    foreshadowing: str
    next_hook: str


class MemoryUpdater:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def run(self, memory: NovelMemory, chapter_number: int, title: str, chapter: str) -> MemoryUpdate:
        prompt = self.client.render_prompt(
            "update_memory.md",
            chapter_number=chapter_number,
            title=title,
            chapter=chapter,
            characters=memory.characters,
            plot_timeline=memory.plot_timeline,
            foreshadowing=memory.foreshadowing,
            chapter_summaries=memory.chapter_summaries,
        )
        result = self.client.chat(prompt, system="你是小说连续性记录员。只更新事实，不引入未发生剧情。", temperature=0.25, max_tokens=5000)
        return MemoryUpdate(
            chapter_summary=section(result, "CHAPTER_SUMMARY") or f"第{chapter_number:03d}章《{title}》已完成。",
            characters=section(result, "CHARACTERS") or memory.characters,
            plot_timeline=section(result, "PLOT_TIMELINE") or memory.plot_timeline,
            foreshadowing=section(result, "FORESHADOWING") or memory.foreshadowing,
            next_hook=section(result, "NEXT_HOOK") or "下一章继续推进主线冲突。",
        )
