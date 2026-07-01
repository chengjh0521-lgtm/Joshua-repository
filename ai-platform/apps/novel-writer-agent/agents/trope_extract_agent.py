from __future__ import annotations

from agents.common import section
from services.deepseek_client import DeepSeekClient


class TropeExtractAgent:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def run(self, market_report: str) -> tuple[str, str]:
        prompt = self.client.render_prompt("trope_extract.md", market_report=market_report)
        result = self.client.chat(prompt, system="你负责提炼可迁移的抽象创作规律，并严格排除可识别抄袭元素。", temperature=0.3, max_tokens=5000)
        trope_library = section(result, "TROPE_LIBRARY") or result
        originality_rules = section(result, "ORIGINALITY_RULES") or "不得复用具体人物、设定、能力体系、世界观、桥段、台词或剧情结构。"
        return trope_library, originality_rules
