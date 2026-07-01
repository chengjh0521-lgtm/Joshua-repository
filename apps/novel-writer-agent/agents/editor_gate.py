from __future__ import annotations

import re

from pydantic import BaseModel

from agents.common import section
from services.deepseek_client import DeepSeekClient
from services.memory_store import NovelMemory


class EditorGateReport(BaseModel):
    passed: bool
    report: str
    editor_score: int
    ai_similarity: int
    information_density: int


def _score(text: str, label: str, default: int) -> int:
    pattern = rf"{re.escape(label)}\s*[：:]\s*(\d+)"
    match = re.search(pattern, text)
    if not match:
        return default
    return max(0, min(100, int(match.group(1))))


class EditorGate:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def judge(self, memory: NovelMemory, chapter_plan: str, chapter: str, attempt: int) -> EditorGateReport:
        prompt = self.client.render_prompt(
            "editor_gate.md",
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
            attempt=attempt,
        )
        result = self.client.chat(
            prompt,
            system="你是番茄小说终审编辑。只做 PASS 或 REJECT，不改写正文。",
            temperature=0.2,
            max_tokens=4000,
        )
        verdict = (section(result, "VERDICT") or "").upper()
        report = section(result, "REPORT") or result
        editor_score = _score(result, "编辑评分", 0)
        ai_similarity = _score(result, "AI相似度", 100)
        information_density = _score(result, "信息密度", 100)
        passed = verdict.startswith("PASS") or (
            editor_score >= 85 and ai_similarity <= 50 and information_density <= 85
        )
        if attempt >= 5 and editor_score >= 80:
            passed = True
        return EditorGateReport(
            passed=passed,
            report=report,
            editor_score=editor_score,
            ai_similarity=ai_similarity,
            information_density=information_density,
        )
