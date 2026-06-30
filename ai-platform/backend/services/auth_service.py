import json
import os
import shutil
import threading
from pathlib import Path

from fastapi import HTTPException, Request, status


SESSION_USER_KEY = "username"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DATA_DIR = PROJECT_ROOT / "backend" / "data"
ACCOUNTS_FILE = BACKEND_DATA_DIR / "accounts.json"
ACCOUNTS_SEED_FILE = BACKEND_DATA_DIR / "accounts.seed.json"
TOKEN_ACTIONS = {"generate", "short", "write", "next"}

_LOCK = threading.RLock()


def _default_data() -> dict:
    return {"accounts": []}


def _ensure_accounts_file() -> None:
    BACKEND_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not ACCOUNTS_FILE.exists():
        if ACCOUNTS_SEED_FILE.exists():
            shutil.copyfile(ACCOUNTS_SEED_FILE, ACCOUNTS_FILE)
        else:
            _save_accounts(_default_data())


def _load_accounts() -> dict:
    _ensure_accounts_file()
    try:
        return json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="账户 JSON 文件格式错误。") from exc


def _save_accounts(data: dict) -> None:
    BACKEND_DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = ACCOUNTS_FILE.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(ACCOUNTS_FILE)


def _accounts(data: dict) -> list[dict]:
    accounts = data.setdefault("accounts", [])
    if not isinstance(accounts, list):
        raise HTTPException(status_code=500, detail="账户 JSON 文件格式错误。")
    return accounts


def _find_account(data: dict, username: str) -> dict | None:
    for account in _accounts(data):
        if account.get("username") == username:
            return account
    return None


def _sync_env_admin(data: dict) -> None:
    username = os.getenv("ADMIN_USERNAME", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "").strip()
    if not username or not password:
        return

    account = _find_account(data, username)
    if account:
        account.update(
            {
                "password": password,
                "role": "admin",
                "enabled": True,
                "quota_limit": None,
                "quota_used": 0,
            }
        )
        return

    _accounts(data).append(
        {
            "username": username,
            "password": password,
            "role": "admin",
            "enabled": True,
            "quota_limit": None,
            "quota_used": 0,
        }
    )


def _account_view(account: dict) -> dict:
    quota_limit = account.get("quota_limit")
    quota_used = int(account.get("quota_used") or 0)
    if quota_limit is None:
        quota_remaining = None
    else:
        quota_remaining = max(0, int(quota_limit) - quota_used)

    return {
        "username": account.get("username"),
        "role": account.get("role", "user"),
        "quota_limit": quota_limit,
        "quota_used": quota_used,
        "quota_remaining": quota_remaining,
    }


def login(request: Request, username: str, password: str) -> dict:
    with _LOCK:
        data = _load_accounts()
        _sync_env_admin(data)
        _save_accounts(data)
        account = _find_account(data, username)

    if not account or not account.get("enabled", True) or account.get("password") != password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误。",
        )

    request.session[SESSION_USER_KEY] = username
    view = _account_view(account)
    return {"authenticated": True, **view}


def logout(request: Request) -> dict:
    request.session.clear()
    return {"authenticated": False}


def current_user(request: Request) -> dict:
    username = request.session.get(SESSION_USER_KEY)
    if not username:
        return {"authenticated": False, "username": None}

    with _LOCK:
        data = _load_accounts()
        _sync_env_admin(data)
        _save_accounts(data)
        account = _find_account(data, username)

    if not account or not account.get("enabled", True):
        request.session.clear()
        return {"authenticated": False, "username": None}

    return {"authenticated": True, **_account_view(account)}


def require_login(request: Request) -> str:
    username = request.session.get(SESSION_USER_KEY)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录后再使用该功能。",
        )

    with _LOCK:
        data = _load_accounts()
        _sync_env_admin(data)
        _save_accounts(data)
        account = _find_account(data, username)

    if not account or not account.get("enabled", True):
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账户不存在或已停用，请重新登录。",
        )
    return username


def is_token_action(payload: dict) -> bool:
    action = str(payload.get("action") or "generate").strip()
    return action in TOKEN_ACTIONS


def ensure_quota_available(username: str) -> None:
    with _LOCK:
        data = _load_accounts()
        account = _find_account(data, username)
        if not account:
            raise HTTPException(status_code=401, detail="账户不存在，请重新登录。")
        quota_limit = account.get("quota_limit")
        if quota_limit is None:
            return
        quota_used = int(account.get("quota_used") or 0)
        if quota_used >= int(quota_limit):
            raise HTTPException(status_code=403, detail="体验次数已用完。")


def consume_quota(username: str) -> dict:
    with _LOCK:
        data = _load_accounts()
        account = _find_account(data, username)
        if not account:
            raise HTTPException(status_code=401, detail="账户不存在，请重新登录。")
        quota_limit = account.get("quota_limit")
        if quota_limit is not None:
            account["quota_used"] = int(account.get("quota_used") or 0) + 1
            _save_accounts(data)
        return _account_view(account)
