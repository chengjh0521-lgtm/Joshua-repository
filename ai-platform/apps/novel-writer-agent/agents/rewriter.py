from __future__ import annotations

from pydantic import BaseModel

from agents.common import section
from services.deepseek_client import DeepSeekClient


class RewriteResult(BaseModel):
    body: str
    notes: str


class Rewriter:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def run(self, chapter: str, review_notes: str, originality_report: str = "") -> RewriteResult:
        prompt = self.client.render_prompt(
            "rewrite_chapter.md",
            chapter=chapter,
            review_notes=review_notes,
            originality_report=originality_report,
        )
        result = self.client.chat(prompt, system="你是中文小说改稿编辑。保留剧情，只提升自然度、画面感和原创性。", temperature=0.65, max_tokens=9000)
        return RewriteResult(
            body=section(result, "CHAPTER") or result,
            notes=section(result, "REWRITE_NOTES") or "已根据审稿意见进行去AI味改写。",
        )
