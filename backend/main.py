import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from backend.services import auth_service
from backend.services.file_service import get_output_file, list_output_files
from backend.services.novel_service import NovelActionError, run_novel_agent


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGENT_ROOT = PROJECT_ROOT / "apps" / "novel-writer-agent"

load_dotenv(PROJECT_ROOT / ".env")

app = FastAPI(title="AI 创作平台", version="0.1.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("APP_SECRET_KEY", "change_this_secret"),
    same_site="lax",
    https_only=False,
)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


class LoginPayload(BaseModel):
    username: str
    password: str


class NovelRunPayload(BaseModel):
    action: str
    goal: str | None = None
    genre: str | None = None
    style: str | None = None
    words: int | None = None


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/auth/login")
async def login(request: Request, payload: LoginPayload):
    return auth_service.login(request, payload.username, payload.password)


@app.post("/api/auth/logout")
async def logout(request: Request):
    return auth_service.logout(request)


@app.get("/api/auth/me")
async def me(request: Request):
    return auth_service.current_user(request)


@app.post("/api/novel/run")
async def novel_run(request: Request, payload: NovelRunPayload):
    auth_service.require_login(request)
    try:
        result = run_novel_agent(AGENT_ROOT, payload.model_dump())
    except NovelActionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(result)


@app.get("/api/novel/files")
async def novel_files(request: Request):
    auth_service.require_login(request)
    return [
        {
            "id": item.id,
            "name": item.name,
            "relative_path": item.relative_path,
            "size": item.size,
            "modified_time": item.modified_time,
        }
        for item in list_output_files(AGENT_ROOT)
    ]


@app.get("/api/novel/files/{file_id}")
async def novel_file(request: Request, file_id: str):
    auth_service.require_login(request)
    try:
        item, content = get_output_file(AGENT_ROOT, file_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PlainTextResponse(
        content,
        media_type="text/plain; charset=utf-8",
        headers={"X-File-Name": item.name},
    )
