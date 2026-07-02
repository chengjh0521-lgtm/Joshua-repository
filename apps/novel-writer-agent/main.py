from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agents.boredom_editor import BoredomEditor
from agents.chapter_planner import ChapterPlanner
from agents.chapter_writer import ChapterWriter
from agents.continuity_agent import ContinuityAgent
from agents.editor_gate import EditorGate
from agents.market_research_agent import MarketResearchAgent
from agents.memory_updater import MemoryUpdater
from agents.originality_guard_agent import OriginalityGuardAgent
from agents.reviewer import Reviewer
from agents.rewriter import Rewriter
from agents.short_story_writer import ShortStoryWriter
from agents.slow_reader import SlowReader
from agents.story_builder_agent import StoryBuilderAgent
from agents.trope_extract_agent import TropeExtractAgent
from config import DATA_DIR, OUTPUT_DIR, PROJECT_ROOT, get_settings
from services.deepseek_client import DeepSeekClient
from services.file_manager import (
    append_text,
    chapter_filename,
    ensure_directories,
    list_clean_chapters,
    read_text,
    sanitize_filename_part,
    short_story_filename,
    write_text,
)
from services.email_sender import send_email
from services.memory_store import MemoryStore
from services.subtitle_converter import parse_duration, txt_to_srt


def make_client() -> DeepSeekClient:
    return DeepSeekClient(get_settings(require_api_key=True))


def build_generation_goal(description: str, min_words: int, max_words: int, max_paragraphs: int) -> str:
    if min_words <= 0:
        raise ValueError("--min-words must be greater than 0.")
    if max_words < min_words:
        raise ValueError("--max-words must be greater than or equal to --min-words.")
    if max_paragraphs <= 0:
        raise ValueError("--max-paragraphs must be greater than 0.")
    return (
        f"{description.strip()}\n\n"
        f"本次生成约束：最少 {min_words} 字，最多 {max_words} 字，"
        f"最多 {max_paragraphs} 个自然段。必须优先遵守这些长度和段落约束。"
    )


def maybe_send_generated_email(args: argparse.Namespace, *, title: str, body: str, attachment_path: Path) -> None:
    if not getattr(args, "send_email", False):
        return
    email_to = getattr(args, "email_to", None)
    if not email_to:
        raise ValueError("--email-to is required when --send-email is enabled.")
    send_email(
        to_email=email_to,
        subject=f"novel-writer-agent 生成内容：{title}",
        body=body,
        attachment_path=attachment_path,
    )
    print(f"已发送邮件到: {email_to}")


def command_init(_: argparse.Namespace) -> None:
    ensure_directories()
    MemoryStore().initialize()
    sample_path = DATA_DIR / "fanqie_top10.txt"
    if not sample_path.exists():
        write_text(
            sample_path,
            "# 手动整理番茄热门前十资料\n\n请按“书名 / 题材 / 标签 / 简介 / 读者看点 / 榜单位置”整理，禁止粘贴小说正文。\n",
        )
    print("初始化完成。请复制 .env.example 为 .env，并填写 DEEPSEEK_API_KEY。")


def command_research(args: argparse.Namespace) -> None:
    store = MemoryStore()
    store.initialize()
    client = make_client()
    input_path = (PROJECT_ROOT / args.input).resolve() if not Path(args.input).is_absolute() else Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    report = MarketResearchAgent(client).run(input_path)
    store.write("market_report.md", report)
    print("已生成 novel_memory/market_report.md")


def command_extract(_: argparse.Namespace) -> None:
    store = MemoryStore()
    store.initialize()
    client = make_client()
    trope_library, originality_rules = TropeExtractAgent(client).run(store.read("market_report.md"))
    store.write("trope_library.md", trope_library)
    store.write("originality_rules.md", originality_rules)
    print("已生成 novel_memory/trope_library.md 和 novel_memory/originality_rules.md")


def command_build(args: argparse.Namespace) -> None:
    store = MemoryStore()
    store.initialize()
    client = make_client()
    bundle = StoryBuilderAgent(client).run(
        genre=args.genre,
        style=args.style,
        trope_library=store.read("trope_library.md"),
        originality_rules=store.read("originality_rules.md"),
    )
    store.write("story_bible.md", bundle.story_bible)
    store.write("outline.md", bundle.outline)
    store.write("characters.md", bundle.characters)
    store.write("world.md", bundle.world)
    store.write("lore_db.json", bundle.lore_db)
    store.write("plot_timeline.md", bundle.plot_timeline)
    store.write("foreshadowing.md", bundle.foreshadowing)
    store.write("chapter_summaries.md", "# 章节摘要\n\n尚未生成章节。")
    store.write("slow_reader.md", "# Slow Reader 长期阅读报告\n\n尚未生成。")
    print("已生成 Professional Novel Pipeline 初始项目文件。")


def run_editorial_pipeline(
    *,
    client: DeepSeekClient,
    memory,
    chapter_number: int,
    chapter_plan: str,
    draft_body: str,
    review_notes: str,
) -> dict:
    final_body = draft_body
    rewrite_notes = ""
    continuity_report = ""
    boredom_report = ""
    editor_report = ""
    slow_reader_report = ""

    for attempt in range(1, 6):
        print(f"Humanizer 去 AI 味改写，第 {attempt} 轮...")
        rewrite = Rewriter(client).run(
            final_body,
            "\n\n".join(
                part
                for part in [review_notes, continuity_report, boredom_report, editor_report, slow_reader_report]
                if part
            ),
        )
        final_body = rewrite.body
        rewrite_notes = rewrite.notes

        print("Continuity 连续性检查...")
        continuity = ContinuityAgent(client).check(memory, chapter_plan, final_body)
        continuity_report = continuity.report
        if not continuity.passed:
            print("Continuity: REJECT，退回 Humanizer。")
            continue

        print("Boredom Editor 无聊度检查...")
        boredom = BoredomEditor(client).judge(chapter_plan, final_body)
        boredom_report = boredom.report
        if not boredom.passed:
            print("Boredom Editor: REJECT，章节缺少呼吸，退回 Humanizer。")
            continue

        print("Editor Gate 终审打分...")
        gate = EditorGate(client).judge(memory, chapter_plan, final_body, attempt)
        editor_report = gate.report
        if not gate.passed:
            print(
                "Editor Gate: REJECT "
                f"(编辑评分 {gate.editor_score}, AI相似度 {gate.ai_similarity}, 信息密度 {gate.information_density})"
            )
            continue

        print("Slow Reader 连续阅读体验检查...")
        slow_reader = SlowReader(client).read(memory, chapter_number, final_body)
        slow_reader_report = slow_reader.report
        if not slow_reader.passed and attempt < 5:
            print("Slow Reader: REJECT，退回 Humanizer。")
            continue

        print("Editor Gate: PASS。")
        return {
            "body": final_body,
            "rewrite_notes": rewrite_notes,
            "continuity_report": continuity_report,
            "boredom_report": boredom_report,
            "editor_report": editor_report,
            "slow_reader_report": slow_reader_report,
        }

    print("编辑部循环达到 5 次，保留最后一版并标记人工复核风险。")
    return {
        "body": final_body,
        "rewrite_notes": rewrite_notes,
        "continuity_report": continuity_report,
        "boredom_report": boredom_report,
        "editor_report": editor_report,
        "slow_reader_report": slow_reader_report,
    }


def command_write(args: argparse.Namespace) -> None:
    store = MemoryStore()
    store.initialize()
    ensure_directories()
    client = make_client()

    chapter_number = len(list_clean_chapters()) + 1
    memory = store.load()
    min_words = getattr(args, "min_words", 100)
    max_words = getattr(args, "max_words", 3000)
    max_paragraphs = getattr(args, "max_paragraphs", 4)
    goal = build_generation_goal(args.goal, min_words, max_words, max_paragraphs)

    print(f"开始生成第{chapter_number:03d}章：规划剧情...")
    chapter_plan = ChapterPlanner(client).run(memory, chapter_number, goal)

    print("生成正文草稿...")
    draft = ChapterWriter(client).run(memory, chapter_number, chapter_plan, goal)

    print("Reviewer 审稿...")
    review_notes = Reviewer(client).run(draft.body, chapter_plan, memory)

    pipeline_result = run_editorial_pipeline(
        client=client,
        memory=memory,
        chapter_number=chapter_number,
        chapter_plan=chapter_plan,
        draft_body=draft.body,
        review_notes=review_notes,
    )
    final_body = pipeline_result["body"]
    rewrite_notes = pipeline_result["rewrite_notes"]

    print("执行原创性检查...")
    guard = OriginalityGuardAgent(client).check(
        final_body,
        memory.originality_rules,
        memory.story_bible,
        memory.trope_library,
    )
    if not guard.passed:
        print("原创性检查提示风险，进行一次定向改写...")
        rewrite = Rewriter(client).run(final_body, review_notes, guard.report)
        final_body = rewrite.body
        rewrite_notes = rewrite.notes
        guard = OriginalityGuardAgent(client).check(
            final_body,
            memory.originality_rules,
            memory.story_bible,
            memory.trope_library,
        )

    print("更新记忆...")
    update = MemoryUpdater(client).run(memory, chapter_number, draft.title, final_body)

    filename = chapter_filename(chapter_number, draft.title)
    clean_path = OUTPUT_DIR / "chapters_clean" / filename
    notes_path = OUTPUT_DIR / "chapters_with_notes" / filename
    write_text(clean_path, final_body)
    write_text(
        notes_path,
        "\n\n".join(
            [
                final_body,
                f"---审稿意见---\n{review_notes}",
                f"---改写说明---\n{rewrite_notes}",
                f"---连续性检查---\n{pipeline_result['continuity_report']}",
                f"---无聊度编辑---\n{pipeline_result['boredom_report']}",
                f"---Editor Gate---\n{pipeline_result['editor_report']}",
                f"---Slow Reader---\n{pipeline_result['slow_reader_report']}",
                f"---原创性检查---\n{'通过' if guard.passed else '仍需人工复核'}\n{guard.report}",
                f"---本章摘要---\n{update.chapter_summary}",
                f"---人物状态更新---\n{update.characters}",
                f"---世界观更新---\n{update.world}",
                f"---Lore Database 更新---\n{update.lore_db}",
                f"---剧情时间线更新---\n{update.plot_timeline}",
                f"---伏笔更新---\n{update.foreshadowing}",
                f"---下一章钩子---\n{update.next_hook}",
                f"---本章规划---\n{chapter_plan}",
            ]
        ),
    )

    append_text(store.path_for("chapter_summaries.md"), update.chapter_summary)
    store.write("characters.md", update.characters)
    store.write("world.md", update.world)
    store.write("lore_db.json", update.lore_db)
    store.write("plot_timeline.md", update.plot_timeline)
    store.write("foreshadowing.md", update.foreshadowing)
    append_text(store.path_for("slow_reader.md"), pipeline_result["slow_reader_report"])

    print(f"已保存 clean: {clean_path}")
    print(f"已保存 with_notes: {notes_path}")
    return {
        "title": draft.title,
        "body": final_body,
        "clean_path": clean_path,
        "notes_path": notes_path,
    }


def command_short(args: argparse.Namespace) -> None:
    store = MemoryStore()
    store.initialize()
    ensure_directories()
    client = make_client()
    max_words = getattr(args, "max_words", getattr(args, "words", 3000))
    min_words = getattr(args, "min_words", 100)
    max_paragraphs = getattr(args, "max_paragraphs", 4)
    remove_ai = getattr(args, "remove_ai", True)
    goal = build_generation_goal(args.goal, min_words, max_words, max_paragraphs)

    print("开始生成完整短篇小说...")
    story = ShortStoryWriter(client).run(
        goal=goal,
        genre=args.genre,
        style=args.style,
        min_words=min_words,
        max_words=max_words,
        max_paragraphs=max_paragraphs,
        remove_ai=remove_ai,
        trope_library=store.read("trope_library.md"),
        originality_rules=store.read("originality_rules.md"),
    )

    print("执行原创性检查...")
    guard = OriginalityGuardAgent(client).check(
        story.body,
        store.read("originality_rules.md"),
        "这是独立短篇小说，不属于长篇 story_bible。",
        store.read("trope_library.md"),
    )

    filename = short_story_filename(story.title)
    clean_path = OUTPUT_DIR / "short_stories" / filename
    notes_path = OUTPUT_DIR / "short_stories_with_notes" / filename
    write_text(clean_path, story.body)
    write_text(
        notes_path,
        "\n\n".join(
            [
                story.body,
                f"---短篇标题---\n{story.title}",
                f"---生成要求---\n{args.goal.strip()}",
                f"---自审与改写说明---\n{story.notes}",
                f"---原创性检查---\n{'通过' if guard.passed else '仍需人工复核'}\n{guard.report}",
            ]
        ),
    )

    print(f"已保存短篇 clean: {clean_path}")
    print(f"已保存短篇 with_notes: {notes_path}")
    return {
        "title": story.title,
        "body": story.body,
        "clean_path": clean_path,
        "notes_path": notes_path,
    }


def command_subtitle(args: argparse.Namespace) -> None:
    ensure_directories()
    if args.max_chars <= 0:
        raise ValueError("--max-chars must be greater than 0.")

    input_path = (PROJECT_ROOT / args.input).resolve() if not Path(args.input).is_absolute() else Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    total_seconds = parse_duration(args.duration)
    text = read_text(input_path)
    srt = txt_to_srt(text, total_seconds, max_chars=args.max_chars)
    cue_count = len([block for block in srt.strip().split("\n\n") if block.strip()])

    if args.output:
        output_path = (PROJECT_ROOT / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output)
    else:
        safe_stem = sanitize_filename_part(input_path.stem, fallback="subtitle")
        duration_label = args.duration.replace(":", "-").replace(".", "_")
        output_path = OUTPUT_DIR / "subtitles" / f"{safe_stem}_{duration_label}.srt"

    write_text(output_path, srt.rstrip())
    print(f"已生成字幕文件: {output_path}")
    print(f"字幕条数: {cue_count}，平均时长: {total_seconds / cue_count:.2f} 秒")
    if total_seconds / cue_count < 1:
        print("提示：平均单条字幕少于 1 秒，可能阅读过快。可以增加 --duration，或调大 --max-chars。")


def command_direct(args: argparse.Namespace) -> None:
    if args.send_email and not args.email_to:
        raise ValueError("--email-to is required when --send-email is enabled.")

    if args.content_type == "长篇":
        result = command_write(
            argparse.Namespace(
                goal=args.description,
                min_words=args.min_words,
                max_words=args.max_words,
                max_paragraphs=args.max_paragraphs,
                remove_ai=args.remove_ai,
            )
        )
    elif args.content_type == "短篇":
        result = command_short(
            argparse.Namespace(
                goal=args.description,
                genre="短篇小说",
                style="自然、有画面感、结尾有余味",
                min_words=args.min_words,
                max_words=args.max_words,
                max_paragraphs=args.max_paragraphs,
                remove_ai=args.remove_ai,
            )
        )
    else:
        raise ValueError("content_type must be 长篇 or 短篇.")

    if result:
        maybe_send_generated_email(
            args,
            title=result["title"],
            body=result["body"],
            attachment_path=result["clean_path"],
        )


def command_status(_: argparse.Namespace) -> None:
    store = MemoryStore()
    store.initialize()
    chapters = list_clean_chapters()
    summaries = store.read("chapter_summaries.md")
    characters = store.read("characters.md")
    world = store.read("world.md")
    lore_db = store.read("lore_db.json")
    foreshadowing = store.read("foreshadowing.md")
    timeline = store.read("plot_timeline.md")
    slow_reader = store.read("slow_reader.md")

    recent_summary = "暂无"
    summary_blocks = [block.strip() for block in summaries.split("\n\n") if block.strip()]
    for block in reversed(summary_blocks):
        if "尚未生成章节" not in block and not block.startswith("#"):
            recent_summary = block
            break

    print(f"已生成章节数：{len(chapters)}")
    if chapters:
        print(f"最近章节文件：{chapters[-1].name}")
    print("\n最近一章摘要：")
    print(recent_summary)
    print("\n主要人物状态：")
    print(characters[:1500].rstrip() or "暂无")
    print("\n未回收伏笔：")
    print(foreshadowing[:1500].rstrip() or "暂无")
    print("\n世界观数据库：")
    print(world[:1500].rstrip() or "暂无")
    print("\nLore Database：")
    print(lore_db[:1500].rstrip() or "暂无")
    print("\nSlow Reader：")
    print(slow_reader[:1500].rstrip() or "暂无")
    print("\n下一章建议：")
    print(_next_suggestion(len(chapters), timeline, foreshadowing))


def _next_suggestion(chapter_count: int, timeline: str, foreshadowing: str) -> str:
    if chapter_count == 0:
        return "先使用 `python main.py write --goal \"写开篇，建立主角困境和第一处悬念\"` 生成第一章。"
    if "未回收" in foreshadowing or "待回收" in foreshadowing:
        return "优先推进一个已埋伏笔，同时制造新的章节钩子。"
    if timeline.strip():
        return "承接上一章结果，推动主线冲突升级，并在结尾留下明确悬念。"
    return "补强人物目标、外部压力和下一处悬念。"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="novel-writer-agent: DeepSeek-only local novel writing agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="初始化项目目录和记忆文件")
    init_parser.set_defaults(func=command_init)

    research_parser = subparsers.add_parser("research", help="根据手动整理的番茄热门资料生成市场报告")
    research_parser.add_argument("--input", required=True, help="例如 data/fanqie_top10.txt")
    research_parser.set_defaults(func=command_research)

    extract_parser = subparsers.add_parser("extract", help="提炼爆款共性和原创性规则")
    extract_parser.set_defaults(func=command_extract)

    build = subparsers.add_parser("build", help="生成原创小说大框架")
    build.add_argument("--genre", required=True)
    build.add_argument("--style", required=True)
    build.set_defaults(func=command_build)

    write = subparsers.add_parser("write", help="只生成下一章")
    write.add_argument("--goal", required=True, help="本章方向要求")
    write.set_defaults(func=command_write)

    next_parser = subparsers.add_parser("next", help="write 命令别名：只生成下一章")
    next_parser.add_argument("--goal", required=True, help="本章方向要求")
    next_parser.set_defaults(func=command_write)

    short = subparsers.add_parser("short", help="生成一个完整原创短篇小说，不更新长篇记忆")
    short.add_argument("--goal", required=True, help="短篇创作要求")
    short.add_argument("--genre", default="悬疑短篇", help="短篇类型，默认：悬疑短篇")
    short.add_argument("--style", default="自然、有画面感、结尾有余味", help="短篇风格")
    short.add_argument("--words", type=int, default=3500, help="目标字数，默认：3500")
    short.set_defaults(func=command_short)

    subtitle = subparsers.add_parser("subtitle", help="把 txt 文件转换为指定总时长的 SRT 字幕")
    subtitle.add_argument("--input", required=True, help="输入 txt 文件路径")
    subtitle.add_argument("--duration", required=True, help="字幕总时长，例如 180、03:00、00:03:00")
    subtitle.add_argument("--output", help="输出 srt 路径，默认保存到 output/subtitles/")
    subtitle.add_argument("--max-chars", type=int, default=24, help="每条字幕最大字符数，默认：24")
    subtitle.set_defaults(func=command_subtitle)

    status = subparsers.add_parser("status", help="查看当前小说状态")
    status.set_defaults(func=command_status)

    return parser


def build_direct_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="直接生成长篇下一章或完整短篇。示例：python main 长篇 \"承接上一章继续写\""
    )
    parser.add_argument("content_type", choices=["长篇", "短篇"], help="生成类型：长篇 或 短篇")
    parser.add_argument("description", help="生成内容描述")
    parser.add_argument("--max-words", type=int, default=3000, help="最大字数，默认：3000")
    parser.add_argument("--min-words", type=int, default=100, help="最小字数，默认：100")
    parser.add_argument("--max-paragraphs", type=int, default=4, help="最大段落数，默认：4")
    parser.add_argument("--remove-ai", action="store_true", help="是否去 AI，默认：否")
    parser.add_argument("--send-email", action="store_true", help="是否发送到邮件，默认：否")
    parser.add_argument("--email-to", help="邮件发送地址。只有 --send-email 时有效，且此时必填")
    return parser


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in {"长篇", "短篇"}:
        parser = build_direct_parser()
        args = parser.parse_args()
        command_direct(args)
        return

    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
