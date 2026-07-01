from __future__ import annotations

from pydantic import BaseModel

from agents.common import section
from services.deepseek_client import DeepSeekClient


class StoryBibleBundle(BaseModel):
    story_bible: str
    outline: str
    characters: str
    world: str
    lore_db: str
    plot_timeline: str
    foreshadowing: str


class StoryBuilderAgent:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def run(self, genre: str, style: str, trope_library: str, originality_rules: str) -> StoryBibleBundle:
        prompt = self.client.render_prompt(
            "build_story_bible.md",
            genre=genre,
            style=style,
            trope_library=trope_library,
            originality_rules=originality_rules,
        )
        result = self.client.chat(prompt, system="你是原创长篇类型小说总编剧。只生成原创设定。", temperature=0.7, max_tokens=7000)
        return StoryBibleBundle(
            story_bible=section(result, "STORY_BIBLE") or result,
            outline=section(result, "OUTLINE"),
            characters=section(result, "CHARACTERS"),
            world=section(result, "WORLD"),
            lore_db=section(result, "LORE_DB"),
            plot_timeline=section(result, "PLOT_TIMELINE"),
            foreshadowing=section(result, "FORESHADOWING"),
        )
