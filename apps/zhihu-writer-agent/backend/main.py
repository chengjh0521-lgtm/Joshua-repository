import json
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.agents.final_check_agent import FinalCheckAgent
from backend.agents.outline_agent import OutlineAgent
from backend.agents.reviewer_agent import ReviewerAgent
from backend.agents.rewrite_agent import RewriteAgent
from backend.agents.writer_agent import WriterAgent
from backend.config import ensure_runtime_dirs
from backend.services.deepseek_client import DeepSeekClient, DeepSeekError
from backend.services.article_style import normalize_answer_style
from backend.services.storage import Storage


app = FastAPI(title="zhihu-writer-agent-deepseek-only", version="0.1.0")
storage = Storage()
DEFAULT_TARGET_WORD_COUNT = 1800
MIN_TARGET_WORD_COUNT = 800
MAX_TARGET_WORD_COUNT = 3500


class GenerateArticleRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=200)
    target_word_count: int | None = Field(default=None)


class GenerateIdeaRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=200)


class ArticleResponse(BaseModel):
    id: int
    topic: str
    title: Optional[str] = None
    status: str
    markdown_path: Optional[str] = None
    text_path: Optional[str] = None
    evaluation: Optional[dict[str, Any]] = None
    final_check: Optional[dict[str, Any]] = None
    error: Optional[str] = None


@app.on_event("startup")
async def startup() -> None:
    ensure_runtime_dirs()
    storage.init_db()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    has_path_error = any(error.get("loc", [None])[0] == "path" for error in errors)
    message = (
        "URL 路径参数不对。latest 要使用 /api/articles/latest，数字 ID 要使用 /api/articles/1 这种格式。"
        if has_path_error
        else "请求体格式不对。请在 JSON 里传入 topic 字段，例如 {\"topic\":\"你的选题\"}。"
    )
    return JSONResponse(
        status_code=422,
        content={
            "message": message,
            "errors": errors,
        },
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.post("/api/articles/generate", response_model=ArticleResponse)
async def generate_article(payload: GenerateArticleRequest) -> ArticleResponse:
    return await generate_article_draft(payload)


@app.post("/api/articles/generate-draft", response_model=ArticleResponse)
async def generate_article_draft(payload: GenerateArticleRequest) -> ArticleResponse:
    target_word_count = clamp_target_word_count(payload.target_word_count)
    article = await _generate_content(
        topic=payload.topic,
        prompt_names={
            "outline": "outline.md",
            "write": "write_article.md",
            "review": "review_article.md",
            "rewrite": "rewrite_article.md",
            "final_check": "final_check.md",
        },
        kind="article",
        target_word_count=target_word_count,
    )

    return _article_response(article)


@app.post("/api/ideas/generate", response_model=ArticleResponse)
async def generate_idea(payload: GenerateIdeaRequest) -> ArticleResponse:
    article = await _generate_content(
        topic=payload.topic,
        prompt_names={
            "outline": "idea_outline.md",
            "write": "idea_write.md",
            "review": "idea_review.md",
            "rewrite": "idea_rewrite.md",
            "final_check": "idea_final_check.md",
        },
        kind="idea",
        target_word_count=None,
    )

    return _article_response(article)


async def _generate_content(
    *,
    topic: str,
    prompt_names: dict[str, str],
    kind: str,
    target_word_count: int | None,
) -> dict[str, Any]:
    article = storage.create_article(topic)
    article_id = article["id"]

    try:
        client = DeepSeekClient()
        outline_agent = OutlineAgent(client, prompt_names["outline"])
        writer_agent = WriterAgent(client, prompt_names["write"])
        reviewer_agent = ReviewerAgent(client, prompt_names["review"])
        rewrite_agent = RewriteAgent(client, prompt_names["rewrite"])
        final_check_agent = FinalCheckAgent(client, prompt_names["final_check"])

        storage.update_article(article_id, status=f"{kind}_topic_accepted_by_user")
        evaluation_json = json.dumps(
            {
                "passed": True,
                "source": "manual_user_input",
                "kind": kind,
                "reasons": ["用户手动输入的选题默认视为已人工审核。"],
                "suggestions": [],
            },
            ensure_ascii=False,
            indent=2,
        )
        storage.update_article(article_id, evaluation_json=evaluation_json)

        storage.update_article(article_id, status="creating_outline")
        outline = await outline_agent.create_outline(topic, evaluation_json, target_word_count)
        storage.update_article(article_id, outline=outline)

        storage.update_article(article_id, status="writing_draft")
        draft = await writer_agent.write(topic, outline, target_word_count)
        storage.update_article(article_id, draft=draft)

        storage.update_article(article_id, status="reviewing_draft")
        review = await reviewer_agent.review(topic, draft, target_word_count)
        storage.update_article(article_id, review=review)

        storage.update_article(article_id, status="rewriting_article")
        final_article = await rewrite_agent.rewrite(topic, draft, review, target_word_count)
        final_article = normalize_answer_style(final_article)
        storage.update_article(article_id, final_article=final_article)

        storage.update_article(article_id, status="final_checking")
        final_check = await final_check_agent.check(topic, final_article, target_word_count)
        final_check_json = json.dumps(final_check.model_dump(), ensure_ascii=False, indent=2)

        text_path = storage.save_text_output(
            title=final_check.suggested_title,
            topic=topic,
            content=final_article,
            kind=kind,
            final_check=final_check.model_dump(),
        )
        final_status = (
            f"{kind}_txt_saved"
            if final_check.recommend_publish
            else "final_checked_not_recommended"
        )
        article = storage.update_article(
            article_id,
            title=final_check.suggested_title,
            status=final_status,
            final_check_json=final_check_json,
            markdown_path=str(text_path),
        )

        return article
    except HTTPException:
        raise
    except (DeepSeekError, Exception) as exc:
        article = storage.update_article(article_id, status="failed", error=str(exc))
        if isinstance(exc, DeepSeekError):
            raise HTTPException(status_code=502, detail=_article_response(article).model_dump())
        raise HTTPException(status_code=500, detail=_article_response(article).model_dump())


@app.get("/api/articles", response_model=list[dict[str, Any]])
async def list_articles() -> list[dict[str, Any]]:
    return storage.list_articles()


@app.get("/api/articles/latest", response_model=dict[str, Any])
async def get_latest_article() -> dict[str, Any]:
    article = storage.get_latest_article()
    if not article:
        raise HTTPException(status_code=404, detail="No article found")
    return article


@app.get("/api/articles/{article_id:int}", response_model=dict[str, Any])
async def get_article(article_id: int) -> dict[str, Any]:
    article = storage.get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


def _article_response(article: dict[str, Any]) -> ArticleResponse:
    return ArticleResponse(
        id=article["id"],
        topic=article["topic"],
        title=article.get("title"),
        status=article["status"],
        markdown_path=article.get("markdown_path"),
        text_path=article.get("text_path") or article.get("markdown_path"),
        evaluation=_json_or_none(article.get("evaluation_json")),
        final_check=_json_or_none(article.get("final_check_json")),
        error=article.get("error"),
    )


def clamp_target_word_count(value: int | None) -> int:
    try:
        target = int(value) if value is not None else DEFAULT_TARGET_WORD_COUNT
    except (TypeError, ValueError):
        target = DEFAULT_TARGET_WORD_COUNT
    return max(MIN_TARGET_WORD_COUNT, min(MAX_TARGET_WORD_COUNT, target))


def _json_or_none(value: Optional[str]) -> Optional[dict[str, Any]]:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None
