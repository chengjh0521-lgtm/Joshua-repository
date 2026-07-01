from __future__ import annotations

from pydantic import BaseModel

from agents.common import section
from services.deepseek_client import DeepSeekClient


class ShortStory(BaseModel):
    title: str
    body: str
    notes: str


class ShortStoryWriter:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def run(
        self,
        *,
        goal: str,
        genre: str,
        style: str,
        min_words: int,
        max_words: int,
        max_paragraphs: int,
        remove_ai: bool,
        trope_library: str,
        originality_rules: str,
    ) -> ShortStory:
        prompt = self.client.render_prompt(
            "short_story_write.md",
            goal=goal,
            genre=genre,
            style=style,
            min_words=min_words,
            max_words=max_words,
            max_paragraphs=max_paragraphs,
            remove_ai_instruction="需要去掉明显 AI 味、空话、模板化句子、套路句。" if remove_ai else "不需要额外执行去 AI 改写，但仍需保持自然中文表达。",
            trope_library=trope_library,
            originality_rules=originality_rules,
        )
        result = self.client.chat(
            prompt,
            system="你是中文短篇小说作者。只写一个完整原创短篇，不写成长篇章节。",
            temperature=0.78,
            max_tokens=9000,
        )
        return ShortStory(
            title=section(result, "TITLE") or "未命名短篇",
            body=section(result, "BODY") or result,
            notes=section(result, "NOTES") or "已生成完整原创短篇。",
        )
