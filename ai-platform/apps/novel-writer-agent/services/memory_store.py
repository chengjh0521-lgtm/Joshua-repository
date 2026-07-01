from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from config import MEMORY_DIR
from services.file_manager import read_text, write_text


SYSTEM_RULES = """# 最高规则

你不是 AI。你是职业网文团队成员。

禁止为了完成任务而生成内容。必须保持人物一致、世界观一致、时间线一致、情绪一致、节奏一致。

任何 Agent 不得擅自增加设定、删除设定、修改世界观、修改人物关系。

所有修改必须遵循：少改。优先删。不要增加。不要解释。保持留白。
"""


MEMORY_DEFAULTS: dict[str, str] = {
    "00_System/system_rules.md": SYSTEM_RULES,
    "01_Planner/novel_bible.md": "# Novel Bible\n\n尚未生成。\n",
    "02_Outline/outline.md": "# 大纲\n\n尚未生成。\n",
    "03_Character/character_db.json": "{\n  \"characters\": []\n}\n",
    "04_World/world_db.json": "{\n  \"world_rules\": [],\n  \"forces\": [],\n  \"locations\": [],\n  \"power_system\": [],\n  \"taboos\": []\n}\n",
    "10_LoreDatabase/lore_db.json": "{\n  \"items\": []\n}\n",
    "11_Memory/chapter_summaries.md": "# 章节摘要\n\n尚未生成章节。\n",
    "11_Memory/plot_timeline.md": "# 剧情时间线\n\n尚未生成。\n",
    "11_Memory/foreshadowing.md": "# 伏笔记录\n\n尚未生成。\n",
    "11_Memory/slow_reader.md": "# Slow Reader 长期阅读报告\n\n尚未生成。\n",
    "11_Memory/market_report.md": "# 市场调研报告\n\n尚未生成。\n",
    "11_Memory/trope_library.md": "# 爆款共性要素库\n\n尚未生成。\n",
    "11_Memory/originality_rules.md": "# 原创性规则\n\n不得抄袭具体人物、设定、能力体系、世界观、桥段、台词或剧情结构。\n",
}


ALIASES: dict[str, str] = {
    "system_rules.md": "00_System/system_rules.md",
    "market_report.md": "11_Memory/market_report.md",
    "trope_library.md": "11_Memory/trope_library.md",
    "originality_rules.md": "11_Memory/originality_rules.md",
    "story_bible.md": "01_Planner/novel_bible.md",
    "outline.md": "02_Outline/outline.md",
    "characters.md": "03_Character/character_db.json",
    "world.md": "04_World/world_db.json",
    "plot_timeline.md": "11_Memory/plot_timeline.md",
    "foreshadowing.md": "11_Memory/foreshadowing.md",
    "lore_db.json": "10_LoreDatabase/lore_db.json",
    "chapter_summaries.md": "11_Memory/chapter_summaries.md",
    "slow_reader.md": "11_Memory/slow_reader.md",
}


class NovelMemory(BaseModel):
    system_rules: str
    market_report: str
    trope_library: str
    originality_rules: str
    story_bible: str
    outline: str
    characters: str
    world: str
    lore_db: str
    plot_timeline: str
    foreshadowing: str
    chapter_summaries: str
    slow_reader: str


class MemoryStore:
    def __init__(self, root: Path | None = None):
        self.root = root or MEMORY_DIR

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        for filename, default in MEMORY_DEFAULTS.items():
            path = self.root / filename
            if not path.exists():
                legacy_name = next((old for old, new in ALIASES.items() if new == filename), "")
                legacy_path = self.root / legacy_name if legacy_name else None
                if legacy_path and legacy_path.exists():
                    write_text(path, read_text(legacy_path))
                else:
                    write_text(path, default)

    def path_for(self, filename: str) -> Path:
        return self.root / ALIASES.get(filename, filename)

    def read(self, filename: str) -> str:
        return read_text(self.path_for(filename))

    def write(self, filename: str, content: str) -> None:
        write_text(self.path_for(filename), content)

    def load(self) -> NovelMemory:
        return NovelMemory(
            system_rules=self.read("system_rules.md"),
            market_report=self.read("market_report.md"),
            trope_library=self.read("trope_library.md"),
            originality_rules=self.read("originality_rules.md"),
            story_bible=self.read("story_bible.md"),
            outline=self.read("outline.md"),
            characters=self.read("characters.md"),
            world=self.read("world.md"),
            lore_db=self.read("lore_db.json"),
            plot_timeline=self.read("plot_timeline.md"),
            foreshadowing=self.read("foreshadowing.md"),
            chapter_summaries=self.read("chapter_summaries.md"),
            slow_reader=self.read("slow_reader.md"),
        )
