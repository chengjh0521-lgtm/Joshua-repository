import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv


AGENT_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = AGENT_ROOT.parents[1]
DATA_DIR = AGENT_ROOT / "data"
OUTPUT_DIR = AGENT_ROOT / "output"
MEMORY_DIR = AGENT_ROOT / "novel_memory"
PROMPTS_DIR = AGENT_ROOT / "prompts"

CHAPTERS_CLEAN_DIR = OUTPUT_DIR / "chapters_clean"
CHAPTERS_WITH_NOTES_DIR = OUTPUT_DIR / "chapters_with_notes"
SHORT_CLEAN_DIR = OUTPUT_DIR / "short_stories"
SHORT_WITH_NOTES_DIR = OUTPUT_DIR / "short_stories_with_notes"

STATE_FILE = MEMORY_DIR / "project_state.json"
LONG_MEMORY_FILE = MEMORY_DIR / "long_novel_memory.json"
RESEARCH_FILE = MEMORY_DIR / "research_notes.txt"
PATTERNS_FILE = MEMORY_DIR / "extracted_patterns.txt"

WINDOWS_FORBIDDEN = r'<>:"/\|?*'


def ensure_dirs() -> None:
    for path in (
        DATA_DIR,
        OUTPUT_DIR,
        MEMORY_DIR,
        PROMPTS_DIR,
        CHAPTERS_CLEAN_DIR,
        CHAPTERS_WITH_NOTES_DIR,
        SHORT_CLEAN_DIR,
        SHORT_WITH_NOTES_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def load_env() -> None:
    load_dotenv(PROJECT_ROOT / ".env")


def safe_filename(value: str, fallback: str = "未命名") -> str:
    cleaned = "".join("_" if char in WINDOWS_FORBIDDEN else char for char in value)
    cleaned = re.sub(r"\s+", "_", cleaned).strip("._ ")
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned[:80] or fallback


def read_text(path: Path, default: str = "") -> str:
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def word_range(min_words: int, max_words: int) -> str:
    return f"{min_words}-{max_words} 字"


def init_project() -> None:
    ensure_dirs()
    if not STATE_FILE.exists():
        save_json(
            STATE_FILE,
            {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "chapter_count": 0,
                "genre": "",
                "style": "",
                "last_goal": "",
            },
        )
    if not LONG_MEMORY_FILE.exists():
        save_json(
            LONG_MEMORY_FILE,
            {
                "premise": "",
                "characters": [],
                "world_rules": [],
                "open_threads": [],
                "chapter_summaries": [],
            },
        )
    print("小说 Agent 已初始化。")
    print(f"记忆目录：{MEMORY_DIR}")
    print(f"输出目录：{OUTPUT_DIR}")


def status() -> None:
    ensure_dirs()
    state = load_json(STATE_FILE, {})
    memory = load_json(LONG_MEMORY_FILE, {})
    chapter_files = sorted(CHAPTERS_CLEAN_DIR.glob("*.txt"))
    short_files = sorted(SHORT_CLEAN_DIR.glob("*.txt"))
    print("小说 Agent 状态")
    print(f"- 已初始化：{'是' if STATE_FILE.exists() else '否'}")
    print(f"- 长篇章节数：{len(chapter_files)}")
    print(f"- 短篇数量：{len(short_files)}")
    print(f"- 当前题材：{state.get('genre', '') or '未设置'}")
    print(f"- 当前风格：{state.get('style', '') or '未设置'}")
    print(f"- 长篇记忆摘要数：{len(memory.get('chapter_summaries', []))}")


def research(input_path: str) -> None:
    ensure_dirs()
    source = (AGENT_ROOT / input_path).resolve()
    if AGENT_ROOT not in source.parents:
        raise SystemExit("input 必须位于 novel-writer-agent 目录内。")
    if not source.exists():
        raise SystemExit(f"找不到调研输入文件：{source}")

    note = (
        "市场调研资料（用户手动整理的公开信息）\n"
        "禁止抓取或复制小说正文，只提炼抽象题材、标签、读者期待和节奏偏好。\n\n"
        f"{source.read_text(encoding='utf-8')}\n"
    )
    write_text(RESEARCH_FILE, note)
    print(f"调研资料已保存：{RESEARCH_FILE}")


def extract_patterns() -> None:
    ensure_dirs()
    notes = read_text(RESEARCH_FILE, "")
    if not notes:
        write_text(
            PATTERNS_FILE,
            "暂无调研资料。可先运行 research 命令导入用户手动整理的公开资料。\n",
        )
    else:
        prompt = (
            "请从以下公开资料中提炼抽象创作共性，禁止复刻具体人物、桥段、台词、设定和世界观。\n\n"
            f"{notes[:8000]}"
        )
        write_text(PATTERNS_FILE, generate_text(prompt, 600, 1000, False, "patterns"))
    print(f"抽象共性已保存：{PATTERNS_FILE}")


def build_project(genre: str, style: str) -> None:
    ensure_dirs()
    state = load_json(STATE_FILE, {})
    memory = load_json(LONG_MEMORY_FILE, {})
    patterns = read_text(PATTERNS_FILE, "暂无抽象共性。")
    prompt = (
        f"请为一个长篇小说项目建立简洁创作记忆。\n题材：{genre or '未指定'}\n"
        f"风格：{style or '未指定'}\n参考抽象共性：{patterns[:4000]}\n"
        "要求：只写原创设定，不抄袭具体作品。"
    )
    memory["premise"] = generate_text(prompt, 700, 1000, False, "build")
    memory.setdefault("characters", [])
    memory.setdefault("world_rules", [])
    memory.setdefault("open_threads", [])
    memory.setdefault("chapter_summaries", [])
    state.update({"genre": genre or "", "style": style or ""})
    save_json(STATE_FILE, state)
    save_json(LONG_MEMORY_FILE, memory)
    print("长篇项目记忆已建立。")


def call_deepseek(prompt: str, max_words: int) -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    if not api_key:
        raise RuntimeError("未配置 DEEPSEEK_API_KEY。")

    response = httpx.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是一个原创写作助手。只创作原创内容，禁止抄袭具体人物、桥段、台词、设定和世界观。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.8,
            "max_tokens": max(1000, min(max_words * 2, 8000)),
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def mock_text(prompt: str, min_words: int, max_words: int, de_ai: bool, purpose: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    de_ai_note = "已要求降低 AI 腔，优先使用具体动作、场景细节和自然句式。" if de_ai else "未启用去 AI 味。"
    if purpose == "short":
        return (
            "标题：雨夜便利店\n\n"
            "凌晨两点，便利店门口的雨水漫过台阶。林澈刚把热柜里的包子重新摆好，门铃就响了。\n\n"
            "进来的男人没有收伞。他站在收银台前，问这里还有没有十年前那种薄荷糖。林澈说早停产了。"
            "男人却指了指柜台下面，说最后一盒被店长锁在铁盒里，钥匙压在验钞机底下。\n\n"
            "林澈笑不出来了。验钞机底下真的有钥匙。铁盒里有一张小票，日期是十年前的今晚，"
            "背面写着一句话：第三个顾客走出门，你就会想起来。\n\n"
            "门铃第二次响起，一个女孩买走了热牛奶。第三次响起前，那个湿透的男人看着林澈，"
            "像看着一面终于愿意照人的镜子。\n\n"
            "林澈这才发现，小票上的签名不是店长，是他自己。\n\n"
            "【备注】这是本地 mock 输出，用于验证流程，不消耗 DeepSeek Token。\n"
            f"【生成时间】{timestamp}\n【字数范围】{word_range(min_words, max_words)}\n【去 AI】{de_ai_note}\n"
            f"【目标】{prompt[:500]}\n"
        )
    if purpose == "patterns":
        return (
            "抽象共性：\n"
            "1. 开篇迅速给出异常事件。\n"
            "2. 主角目标清晰，并立刻承受代价。\n"
            "3. 每章结尾留下新的问题，但答案应当在前文埋有线索。\n"
            "4. 爽点来自信息差、选择压力和反转后的合理性，而不是复制具体桥段。\n"
        )
    if purpose == "build":
        return (
            "长篇记忆草案：主角因一次异常委托进入隐藏秩序的边缘。故事以现实细节托底，"
            "每章推进一个可验证线索，同时扩大主角必须承担的代价。"
        )
    return (
        "标题：异常委托\n\n"
        "钟声响起时，主角收到一份没有发件人的委托。它要求他在午夜前找到一个不存在的地址，"
        "否则昨天已经发生过的事故会再次发生。\n\n"
        "他起初以为这是恶作剧，直到手机里出现一段十分钟后才会拍下的视频。视频中的他站在雨里，"
        "手中握着一枚陌生钥匙，身后有人轻声叫出了他的真名。\n\n"
        "【备注】这是本地 mock 输出，用于验证流程，不消耗 DeepSeek Token。\n"
        f"【生成时间】{timestamp}\n【字数范围】{word_range(min_words, max_words)}\n【去 AI】{de_ai_note}\n"
        f"【目标】{prompt[:500]}\n"
    )


def generate_text(prompt: str, min_words: int, max_words: int, de_ai: bool, purpose: str) -> str:
    load_env()
    mock_enabled = os.getenv("NOVEL_AGENT_MOCK", "true").lower() != "false"
    if mock_enabled:
        return mock_text(prompt, min_words, max_words, de_ai, purpose)
    return call_deepseek(prompt, max_words)


def split_notes(content: str) -> tuple[str, str]:
    marker = "【备注】"
    if marker not in content:
        return content.strip() + "\n", content.strip() + "\n"
    clean = content.split(marker, 1)[0].strip() + "\n"
    return clean, content.strip() + "\n"


def title_from_content(content: str, fallback: str) -> str:
    first_line = next((line.strip() for line in content.splitlines() if line.strip()), "")
    first_line = re.sub(r"^标题[:：]\s*", "", first_line)
    return safe_filename(first_line, fallback)


def de_ai_instruction(de_ai: bool) -> str:
    if not de_ai:
        return "不需要额外去 AI 味处理。"
    return (
        "请降低 AI 腔：减少空泛总结和套路化转折，多用具体动作、感官细节、人物选择和自然短句；"
        "避免过度整齐的排比、模板化段落和说教式结尾。"
    )


def write_chapter(goal: str, genre: str, style: str, min_words: int, max_words: int, de_ai: bool, is_next: bool) -> None:
    ensure_dirs()
    state = load_json(STATE_FILE, {"chapter_count": 0})
    memory = load_json(LONG_MEMORY_FILE, {})
    chapter_number = int(state.get("chapter_count", 0)) + 1
    prompt = (
        f"请写长篇小说第 {chapter_number:03d} 章。\n"
        f"题材：{genre or state.get('genre') or '未指定'}\n"
        f"风格：{style or state.get('style') or '未指定'}\n"
        f"字数范围：{word_range(min_words, max_words)}\n"
        f"用户描述：{goal}\n"
        f"{de_ai_instruction(de_ai)}\n"
        f"长篇记忆：{json.dumps(memory, ensure_ascii=False)[:5000]}\n"
        "要求：只生成本章，不一次性生成整本；保持原创。"
    )
    content = generate_text(prompt, min_words, max_words, de_ai, purpose="chapter")
    clean, with_notes = split_notes(content)
    title = title_from_content(content, f"第{chapter_number:03d}章")
    filename = f"第{chapter_number:03d}章_{title}.txt"
    write_text(CHAPTERS_CLEAN_DIR / filename, clean)
    write_text(CHAPTERS_WITH_NOTES_DIR / filename, with_notes)

    memory.setdefault("chapter_summaries", []).append(
        {
            "chapter": chapter_number,
            "goal": goal,
            "title": title,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "summary": clean[:300],
        }
    )
    state.update(
        {
            "chapter_count": chapter_number,
            "last_goal": goal,
            "genre": genre or state.get("genre", ""),
            "style": style or state.get("style", ""),
        }
    )
    save_json(STATE_FILE, state)
    save_json(LONG_MEMORY_FILE, memory)
    print(f"章节已生成：{filename}")
    print(f"模式：{'next' if is_next else 'write'}")


def write_short(goal: str, genre: str, style: str, min_words: int, max_words: int, de_ai: bool) -> None:
    ensure_dirs()
    prompt = (
        "请写一个独立短篇，不更新长篇记忆。\n"
        f"题材：{genre or '未指定'}\n风格：{style or '未指定'}\n"
        f"字数范围：{word_range(min_words, max_words)}\n用户描述：{goal}\n"
        f"{de_ai_instruction(de_ai)}\n"
        "要求：原创，结尾有余味，禁止抄袭具体作品。"
    )
    content = generate_text(prompt, min_words, max_words, de_ai, purpose="short")
    clean, with_notes = split_notes(content)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    title = title_from_content(content, "独立短篇")
    filename = f"短篇_{timestamp}_{title}.txt"
    write_text(SHORT_CLEAN_DIR / filename, clean)
    write_text(SHORT_WITH_NOTES_DIR / filename, with_notes)
    print(f"短篇已生成：{filename}")


def normalize_word_args(args: argparse.Namespace) -> tuple[int, int]:
    max_words = args.max_words or args.words or 2500
    min_words = args.min_words or max(100, int(max_words * 0.8))
    if min_words > max_words:
        raise SystemExit("最小字数不能大于最大字数。")
    return min_words, max_words


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="novel-writer-agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init")
    subparsers.add_parser("status")

    research_parser = subparsers.add_parser("research")
    research_parser.add_argument("--input", required=True)

    subparsers.add_parser("extract")

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--genre", default="")
    build_parser.add_argument("--style", default="")

    for name in ("write", "next", "short"):
        action_parser = subparsers.add_parser(name)
        action_parser.add_argument("--goal", default="")
        action_parser.add_argument("--genre", default="")
        action_parser.add_argument("--style", default="")
        action_parser.add_argument("--words", type=int, default=None)
        action_parser.add_argument("--min-words", type=int, default=None)
        action_parser.add_argument("--max-words", type=int, default=None)
        action_parser.add_argument("--de-ai", action="store_true")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dirs()
    if args.command == "init":
        init_project()
    elif args.command == "status":
        status()
    elif args.command == "research":
        research(args.input)
    elif args.command == "extract":
        extract_patterns()
    elif args.command == "build":
        build_project(args.genre, args.style)
    elif args.command in {"write", "next", "short"}:
        if not args.goal:
            raise SystemExit(f"{args.command} 需要 --goal。")
        min_words, max_words = normalize_word_args(args)
        if args.command == "short":
            write_short(args.goal, args.genre, args.style, min_words, max_words, args.de_ai)
        else:
            write_chapter(
                args.goal,
                args.genre,
                args.style,
                min_words,
                max_words,
                args.de_ai,
                is_next=args.command == "next",
            )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Agent 执行失败：{exc}", file=sys.stderr)
        raise SystemExit(1)
