from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from .user_config_service import user_root


DEFAULT_SHORT_STATE_ID = "short"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _state_store_path(username: str) -> Path:
    root = user_root(username) / "novel"
    root.mkdir(parents=True, exist_ok=True)
    return root / "states.json"


def _states_root(username: str) -> Path:
    root = user_root(username) / "novel" / "states"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _default_state() -> dict:
    return {
        "id": DEFAULT_SHORT_STATE_ID,
        "name": "短篇",
        "mode": "short",
        "genre": "",
        "style": "",
        "setting": "独立短篇状态。每次生成都只根据本次描述创作，不读取或延续过往记忆。",
        "created_at": _now(),
        "updated_at": _now(),
    }


def _default_store() -> dict:
    return {"selected_state_id": DEFAULT_SHORT_STATE_ID, "states": [_default_state()]}


def _load_store(username: str) -> dict:
    path = _state_store_path(username)
    if not path.exists():
        store = _default_store()
        _save_store(username, store)
        return store
    try:
        store = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        store = _default_store()
    states = store.get("states")
    if not isinstance(states, list):
        states = []
    if not any(state.get("id") == DEFAULT_SHORT_STATE_ID for state in states if isinstance(state, dict)):
        states.insert(0, _default_state())
    store["states"] = [_normalize_state(state) for state in states if isinstance(state, dict)]
    if not any(state["id"] == store.get("selected_state_id") for state in store["states"]):
        store["selected_state_id"] = DEFAULT_SHORT_STATE_ID
    _save_store(username, store)
    return store


def _save_store(username: str, store: dict) -> dict:
    path = _state_store_path(username)
    temp_path = path.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)
    return store


def _normalize_state(state: dict) -> dict:
    state_id = str(state.get("id") or "").strip() or uuid.uuid4().hex[:12]
    mode = str(state.get("mode") or "long").strip()
    if state_id == DEFAULT_SHORT_STATE_ID:
        mode = "short"
    elif mode not in {"short", "long"}:
        mode = "long"
    return {
        "id": state_id,
        "name": str(state.get("name") or ("短篇" if mode == "short" else "未命名小说")).strip(),
        "mode": mode,
        "genre": str(state.get("genre") or "").strip(),
        "style": str(state.get("style") or "").strip(),
        "setting": str(state.get("setting") or "").strip(),
        "created_at": str(state.get("created_at") or _now()),
        "updated_at": str(state.get("updated_at") or _now()),
    }


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("._")
    return cleaned or uuid.uuid4().hex[:12]


def state_runtime_root(username: str, state_id: str) -> Path:
    root = _states_root(username) / _slug(state_id)
    (root / "memory").mkdir(parents=True, exist_ok=True)
    (root / "output").mkdir(parents=True, exist_ok=True)
    return root


def state_env(username: str, state_id: str) -> dict[str, str]:
    root = state_runtime_root(username, state_id)
    return {
        "NOVEL_AGENT_MEMORY_DIR": str((root / "memory").resolve()),
        "NOVEL_AGENT_OUTPUT_DIR": str((root / "output").resolve()),
        "NOVEL_AGENT_DATA_DIR": str((root / "data").resolve()),
    }


def output_agent_root(username: str, state_id: str) -> Path:
    return state_runtime_root(username, state_id)


def list_states(username: str) -> dict:
    return _load_store(username)


def get_state(username: str, state_id: str | None) -> dict:
    store = _load_store(username)
    wanted = state_id or store.get("selected_state_id") or DEFAULT_SHORT_STATE_ID
    for state in store["states"]:
        if state["id"] == wanted:
            store["selected_state_id"] = wanted
            _save_store(username, store)
            return state
    raise ValueError("小说状态不存在。")


def create_state(username: str, payload: dict) -> dict:
    store = _load_store(username)
    state = _normalize_state(
        {
            "id": uuid.uuid4().hex[:12],
            "name": payload.get("name") or "新小说",
            "mode": payload.get("mode") or "long",
            "genre": payload.get("genre") or "",
            "style": payload.get("style") or "",
            "setting": payload.get("setting") or "",
        }
    )
    store["states"].append(state)
    store["selected_state_id"] = state["id"]
    return _save_store(username, store)


def update_state(username: str, state_id: str, payload: dict) -> dict:
    store = _load_store(username)
    for index, state in enumerate(store["states"]):
        if state["id"] != state_id:
            continue
        merged = {**state, **payload, "id": state_id, "updated_at": _now()}
        if state_id == DEFAULT_SHORT_STATE_ID:
            merged["mode"] = "short"
            merged["name"] = payload.get("name") or state.get("name") or "短篇"
        store["states"][index] = _normalize_state(merged)
        return _save_store(username, store)
    raise ValueError("小说状态不存在。")


def delete_state(username: str, state_id: str) -> dict:
    if state_id == DEFAULT_SHORT_STATE_ID:
        raise ValueError("默认短篇状态不能删除。")
    store = _load_store(username)
    next_states = [state for state in store["states"] if state["id"] != state_id]
    if len(next_states) == len(store["states"]):
        raise ValueError("小说状态不存在。")
    store["states"] = next_states
    if store.get("selected_state_id") == state_id:
        store["selected_state_id"] = DEFAULT_SHORT_STATE_ID
    runtime_root = state_runtime_root(username, state_id)
    states_root = _states_root(username).resolve()
    resolved_runtime_root = runtime_root.resolve()
    try:
        resolved_runtime_root.relative_to(states_root)
    except ValueError as exc:
        raise ValueError("状态目录非法，已取消删除。") from exc
    shutil.rmtree(resolved_runtime_root, ignore_errors=True)
    return _save_store(username, store)
