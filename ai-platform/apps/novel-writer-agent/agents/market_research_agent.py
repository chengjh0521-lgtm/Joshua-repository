from __future__ import annotations

from pathlib import Path

from services.deepseek_client import DeepSeekClient


class MarketResearchAgent:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def run(self, input_path: Path) -> str:
        source = input_path.read_text(encoding="utf-8")
        prompt = self.client.render_prompt("market_research.md", source=source)
        return self.client.chat(prompt, system="你是严谨的中文网文市场分析师。只分析用户提供的公开资料，不补造正文内容。", temperature=0.35, max_tokens=5000)
