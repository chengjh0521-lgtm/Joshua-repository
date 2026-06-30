import os
from dataclasses import dataclass

from fastapi import HTTPException, Request, status


SESSION_USER_KEY = "admin_username"


@dataclass(frozen=True)
class AuthConfig:
    username: str
    password: str


def get_auth_config() -> AuthConfig:
    return AuthConfig(
        username=os.getenv("ADMIN_USERNAME", "admin"),
        password=os.getenv("ADMIN_PASSWORD", "change_this_password"),
    )


def login(request: Request, username: str, password: str) -> dict:
    config = get_auth_config()
    if username != config.username or password != config.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误。",
        )

    request.session[SESSION_USER_KEY] = username
    return {"authenticated": True, "username": username}


def logout(request: Request) -> dict:
    request.session.clear()
    return {"authenticated": False}


def current_user(request: Request) -> dict:
    username = request.session.get(SESSION_USER_KEY)
    return {"authenticated": bool(username), "username": username}


def require_login(request: Request) -> str:
    username = request.session.get(SESSION_USER_KEY)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录后再使用该功能。",
        )
    return username
