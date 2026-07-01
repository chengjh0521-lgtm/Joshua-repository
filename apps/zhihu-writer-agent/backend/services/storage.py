import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from backend.config import ensure_runtime_dirs, settings


def utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def slugify(value: str, max_length: int = 60) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|\r\n\t]+", "-", value).strip(" .-")
    cleaned = re.sub(r"\s+", "-", cleaned)
    return cleaned[:max_length] or "article"


class Storage:
    def __init__(self) -> None:
        ensure_runtime_dirs()
        self.db_path = settings.database_path
        self.articles_dir = settings.articles_dir
        self.txt_outputs_dir = settings.txt_outputs_dir
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    title TEXT,
                    status TEXT NOT NULL,
                    evaluation_json TEXT,
                    outline TEXT,
                    draft TEXT,
                    review TEXT,
                    final_article TEXT,
                    final_check_json TEXT,
                    markdown_path TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create_article(self, topic: str) -> dict[str, Any]:
        now = utc_now()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO articles (topic, status, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (topic, "created", now, now),
            )
            article_id = int(cursor.lastrowid)
        return self.get_article(article_id) or {}

    def update_article(self, article_id: int, **fields: Any) -> dict[str, Any]:
        if not fields:
            return self.get_article(article_id) or {}

        fields["updated_at"] = utc_now()
        assignments = ", ".join(f"{name} = ?" for name in fields)
        values = list(fields.values()) + [article_id]

        with self.connect() as conn:
            conn.execute(
                f"UPDATE articles SET {assignments} WHERE id = ?",
                values,
            )
        return self.get_article(article_id) or {}

    def get_article(self, article_id: int) -> Optional[dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
        return dict(row) if row else None

    def get_latest_article(self) -> Optional[dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM articles ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    def list_articles(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, topic, title, status, markdown_path, created_at, updated_at
                FROM articles
                ORDER BY id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def save_markdown(
        self,
        *,
        article_id: int,
        title: str,
        topic: str,
        article: str,
        final_check: dict[str, Any],
    ) -> Path:
        filename = f"{article_id:04d}-{slugify(title)}.md"
        path = self.articles_dir / filename
        content = self.render_markdown(title, topic, article, final_check)
        path.write_text(content, encoding="utf-8")
        return path

    def save_text_output(
        self,
        *,
        title: str,
        topic: str,
        content: str,
        kind: str,
        final_check: dict[str, Any],
    ) -> Path:
        date_folder = datetime.now().strftime("%Y-%m-%d")
        question_folder = slugify(topic, max_length=80)
        filename = "long_article.txt" if kind == "article" else "idea.txt"
        output_dir = self.txt_outputs_dir / date_folder / question_folder
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            output_dir = self.articles_dir
            filename = f"{date_folder}-{question_folder}-{filename}"

        path = output_dir / filename
        text = self.render_text(title=title, topic=topic, content=content, kind=kind, final_check=final_check)
        path.write_text(text, encoding="utf-8")
        return path

    @staticmethod
    def render_text(title: str, topic: str, content: str, kind: str, final_check: dict[str, Any]) -> str:
        label = "长文章" if kind == "article" else "想法"
        notes = "\n".join(f"- {item}" for item in final_check.get("final_notes", []))
        return (
            f"类型：{label}\n"
            f"选题：{topic}\n"
            f"标题：{title}\n"
            f"建议发布：{final_check.get('recommend_publish')}\n"
            f"风险等级：{final_check.get('risk_level')}\n\n"
            f"{content.strip()}\n\n"
            f"终审意见：\n{notes or '- 无'}\n"
        )

    @staticmethod
    def render_markdown(title: str, topic: str, article: str, final_check: dict[str, Any]) -> str:
        notes = "\n".join(f"- {item}" for item in final_check.get("final_notes", []))
        manual_suggestions = "\n".join(
            f"- {item}" for item in final_check.get("manual_operation_suggestions", [])
        )
        metadata = {
            "topic": topic,
            "recommend_publish": final_check.get("recommend_publish"),
            "risk_level": final_check.get("risk_level"),
        }
        return (
            f"# {title}\n\n"
            f"<!--\n"
            f"{json.dumps(metadata, ensure_ascii=False, indent=2)}\n"
            f"-->\n\n"
            f"{article.strip()}\n\n"
            f"## 发布前终审\n\n"
            f"{notes or '- 无'}\n\n"
            f"## 人工操作建议\n\n"
            f"{manual_suggestions or '- 无'}\n"
        )
