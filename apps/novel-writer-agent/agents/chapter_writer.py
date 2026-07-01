from __future__ import annotations

from pydantic import BaseModel

from agents.common import section
from services.deepseek_client import DeepSeekClient
from services.memory_store import NovelMemory


class DraftChapter(BaseModel):
    title: str
    body: str


class ChapterWriter:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def run(self, memory: NovelMemory, chapter_number: int, chapter_plan: str, goal: str) -> DraftChapter:
        prompt = self.client.render_prompt(
            "chapter_write.md",
            chapter_number=chapter_number,
            goal=goal,
            chapter_plan=chapter_plan,
            story_bible=memory.story_bible,
            characters=memory.characters,
            plot_timeline=memory.plot_timeline,
            foreshadowing=memory.foreshadowing,
            chapter_summaries=memory.chapter_summaries,
        )
        result = self.client.chat(prompt, system="你是中文类型小说作者。只写当前一章正文。", temperature=0.78, max_tokens=9000)
        return DraftChapter(
            title=section(result, "TITLE") or f"第{chapter_number:03d}章",
            body=section(result, "BODY") or result,
        )
