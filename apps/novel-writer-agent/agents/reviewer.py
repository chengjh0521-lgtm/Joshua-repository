from __future__ import annotations

from services.deepseek_client import DeepSeekClient
from services.memory_store import NovelMemory


class Reviewer:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def run(self, chapter: str, chapter_plan: str, memory: NovelMemory) -> str:
        prompt = self.client.render_prompt(
            "review_chapter.md",
            chapter=chapter,
            chapter_plan=chapter_plan,
            story_bible=memory.story_bible,
            characters=memory.characters,
            plot_timeline=memory.plot_timeline,
            foreshadowing=memory.foreshadowing,
        )
        return self.client.chat(prompt, system="你是网文审稿编辑，专门指出AI味、空话和承接问题。", temperature=0.25, max_tokens=3500)
