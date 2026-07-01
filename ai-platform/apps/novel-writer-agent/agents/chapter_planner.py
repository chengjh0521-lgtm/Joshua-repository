from __future__ import annotations

from services.deepseek_client import DeepSeekClient
from services.memory_store import NovelMemory


class ChapterPlanner:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def run(self, memory: NovelMemory, chapter_number: int, goal: str) -> str:
        prompt = self.client.render_prompt(
            "chapter_plan.md",
            chapter_number=chapter_number,
            goal=goal,
            story_bible=memory.story_bible,
            characters=memory.characters,
            plot_timeline=memory.plot_timeline,
            foreshadowing=memory.foreshadowing,
            chapter_summaries=memory.chapter_summaries,
            originality_rules=memory.originality_rules,
        )
        return self.client.chat(prompt, system="你是章节编剧，只规划当前一章，不提前写后续章节。", temperature=0.55, max_tokens=4000)
