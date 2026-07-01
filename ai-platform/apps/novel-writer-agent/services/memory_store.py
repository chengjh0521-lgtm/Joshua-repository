from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from config import MEMORY_DIR
from services.file_manager import read_text, write_text


MEMORY_DEFAULTS: dict[str, str] = {
    "market_report.md": "# 市场调研报告\n\n尚未生成。\n",
    "trope_library.md": "# 爆款共性要素库\n\n尚未生成。\n",
    "originality_rules.md": "# 原创性规则\n\n不得抄袭具体人物、设定、能力体系、世界观、桥段、台词或剧情结构。\n",
    "story_bible.md": "# 小说大框架\n\n尚未生成。\n",
    "characters.md": "# 人物状态\n\n尚未生成。\n",
    "plot_timeline.md": "# 剧情时间线\n\n尚未生成。\n",
    "foreshadowing.md": "# 伏笔记录\n\n尚未生成。\n",
    "chapter_summaries.md": "# 章节摘要\n\n尚未生成章节。\n",
}


class NovelMemory(BaseModel):
    market_report: str
    trope_library: str
    originality_rules: str
    story_bible: str
    characters: str
    plot_timeline: str
    foreshadowing: str
    chapter_summaries: str


class MemoryStore:
    def __init__(self, root: Path | None = None):
        self.root = root or MEMORY_DIR

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        for filename, default in MEMORY_DEFAULTS.items():
            path = self.root / filename
            if not path.exists():
                write_text(path, default)

    def read(self, filename: str) -> str:
        return read_text(self.root / filename)

    def write(self, filename: str, content: str) -> None:
        write_text(self.root / filename, content)

    def load(self) -> NovelMemory:
        return NovelMemory(
            market_report=self.read("market_report.md"),
            trope_library=self.read("trope_library.md"),
            originality_rules=self.read("originality_rules.md"),
            story_bible=self.read("story_bible.md"),
            characters=self.read("characters.md"),
            plot_timeline=self.read("plot_timeline.md"),
            foreshadowing=self.read("foreshadowing.md"),
            chapter_summaries=self.read("chapter_summaries.md"),
        )
