import os
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from backend.services import auth_service
from backend.services.email_service import EmailConfigError, EmailSendError, send_generated_file_email
from backend.services.file_service import get_output_file, list_output_files
from backend.services.novel_service import NovelActionError, run_novel_agent
from backend.services.user_config_service import add_video_channel, list_video_channels, public_config, save_upload, update_config
from backend.services.video_agent_service import (
    VideoAgentError,
    complete_bilibili_login,
    run_video_agent,
    start_bilibili_login,
    start_video_monitor,
    stop_video_monitor,
    video_monitor_status,
)
from backend.services.zhihu_agent_service import ZhihuAgentError, get_zhihu_output_file, run_zhihu_agent


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGENT_ROOT = PROJECT_ROOT / "apps" / "novel-writer-agent"

load_dotenv(PROJECT_ROOT / ".env")

app = FastAPI(title="AI 创作平台", version="0.2.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("APP_SECRET_KEY", "change_this_secret"),
    same_site="lax",
    https_only=False,
)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def attachment_headers(name: str) -> dict[str, str]:
    ascii_name = "".join(char if ord(char) < 128 and char not in {'"', "\\"} else "_" for char in name) or "download.txt"
    return {
        "X-File-Name": name,
        "Content-Disposition": f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name)}",
    }


class LoginPayload(BaseModel):
    username: str
    password: str


class NovelRunPayload(BaseModel):
    action: str = "generate"
    article_type: str | None = None
    min_words: int | None = None
    max_words: int | None = None
    description: str | None = None
    style: str | None = None
    de_ai: bool = False
    send_email: bool = False
    email_to: str | None = None

    # Backward-compatible fields kept for the first MVP API shape.
    goal: str | None = None
    genre: str | None = None
    words: int | None = None


class UserConfigPayload(BaseModel):
    email_receiver: str | None = None
    video_service_type: str | None = None
    video_notify_mode: str | None = None
    video_publish_mode: str | None = None
    auto_publish: bool | None = None
    auto_publish_bilibili: bool | None = None
    auto_publish_douyin: bool | None = None


class VideoRunPayload(BaseModel):
    action: str = "status"


class VideoChannelPayload(BaseModel):
    name: str
    url: str


class ZhihuRunPayload(BaseModel):
    kind: str = "article"
    topic: str


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    response = templates.TemplateResponse("index.html", {"request": request})
    response.headers["Cache-Control"] = "no-store"
    return response


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


@app.get("/api/user/config")
async def get_user_config(request: Request):
    username = auth_service.require_login(request)
    return public_config(username)


@app.post("/api/user/config")
async def post_user_config(request: Request, payload: UserConfigPayload):
    username = auth_service.require_login(request)
    update_config(username, payload.model_dump(exclude_none=True))
    return public_config(username)


@app.post("/api/user/config/files")
async def post_user_config_files(
    request: Request,
    bilibili_state: UploadFile | None = File(default=None),
    douyin_state: UploadFile | None = File(default=None),
    youtube_cookie: UploadFile | None = File(default=None),
):
    username = auth_service.require_login(request)
    result = public_config(username)
    if bilibili_state is not None:
        result = await save_upload(username, "bilibili_state", bilibili_state)
    if douyin_state is not None:
        result = await save_upload(username, "douyin_state", douyin_state)
    if youtube_cookie is not None:
        result = await save_upload(username, "youtube_cookie", youtube_cookie)
    return result


@app.post("/api/novel/run")
async def novel_run(request: Request, payload: NovelRunPayload):
    username = auth_service.require_login(request)
    data = payload.model_dump()
    should_consume_quota = auth_service.is_token_action(data)
    if should_consume_quota:
        auth_service.ensure_quota_available(username)

    try:
        result = run_novel_agent(AGENT_ROOT, data)
    except NovelActionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if should_consume_quota and result.get("returncode") == 0:
        result["account"] = {"authenticated": True, **auth_service.consume_quota(username)}
    else:
        result["account"] = auth_service.current_user(request)

    result["email"] = {"requested": payload.send_email, "sent": False, "message": ""}
    if payload.send_email and result.get("returncode") == 0 and result.get("latest_file"):
        try:
            send_generated_file_email(
                agent_root=AGENT_ROOT,
                relative_path=result["latest_file"]["relative_path"],
                to_address=payload.email_to or "",
            )
            result["email"] = {
                "requested": True,
                "sent": True,
                "message": f"已发送到 {payload.email_to}",
            }
        except (EmailConfigError, EmailSendError, FileNotFoundError) as exc:
            result["email"] = {
                "requested": True,
                "sent": False,
                "message": f"邮件未发送：{exc}",
            }

    return JSONResponse(result)


@app.post("/api/video/run")
async def video_run(request: Request, payload: VideoRunPayload):
    username = auth_service.require_login(request)
    try:
        result = run_video_agent(PROJECT_ROOT, username, payload.action)
    except VideoAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(result)


@app.post("/api/video/service/start")
async def video_service_start(request: Request):
    username = auth_service.require_login(request)
    try:
        result = start_video_monitor(PROJECT_ROOT, username)
    except VideoAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(result)


@app.post("/api/video/service/stop")
async def video_service_stop(request: Request):
    username = auth_service.require_login(request)
    return JSONResponse(stop_video_monitor(username))


@app.get("/api/video/service/status")
async def video_service_status(request: Request):
    username = auth_service.require_login(request)
    return JSONResponse(video_monitor_status(username))


@app.get("/api/video/channels")
async def video_channels(request: Request):
    username = auth_service.require_login(request)
    return list_video_channels(username)


@app.post("/api/video/channels")
async def add_video_channel_route(request: Request, payload: VideoChannelPayload):
    username = auth_service.require_login(request)
    try:
        return add_video_channel(username, payload.name, payload.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/video/bilibili-login/start")
async def video_bilibili_login_start(request: Request):
    username = auth_service.require_login(request)
    try:
        result = start_bilibili_login(PROJECT_ROOT, username)
    except VideoAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(result)


@app.post("/api/video/bilibili-login/complete")
async def video_bilibili_login_complete(request: Request):
    username = auth_service.require_login(request)
    return JSONResponse(complete_bilibili_login(username))


@app.post("/api/zhihu/run")
async def zhihu_run(request: Request, payload: ZhihuRunPayload):
    auth_service.require_login(request)
    try:
        result = run_zhihu_agent(PROJECT_ROOT, payload.kind, payload.topic)
    except ZhihuAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(result)


@app.get("/api/zhihu/files/{file_id}")
async def zhihu_file(request: Request, file_id: str, download: bool = False):
    auth_service.require_login(request)
    try:
        name, content = get_zhihu_output_file(PROJECT_ROOT, file_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    headers = attachment_headers(name) if download else {"X-File-Name": name}
    return PlainTextResponse(content, media_type="text/plain; charset=utf-8", headers=headers)


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
async def novel_file(request: Request, file_id: str, download: bool = False):
    auth_service.require_login(request)
    try:
        item, content = get_output_file(AGENT_ROOT, file_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    headers = attachment_headers(item.name) if download else {"X-File-Name": item.name}
    return PlainTextResponse(content, media_type="text/plain; charset=utf-8", headers=headers)
