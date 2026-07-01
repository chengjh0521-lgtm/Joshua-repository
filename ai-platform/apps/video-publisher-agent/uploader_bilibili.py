# -*- coding: utf-8 -*-

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from playwright.sync_api import sync_playwright

from config import CONFIG


BASE_DIR = Path(__file__).resolve().parent
TASKS_FILE = Path(CONFIG["publish_tasks_file"])
STATE_FILE = Path(CONFIG["bilibili_state_file"])
UPLOAD_URL = CONFIG.get(
    "bilibili_upload_url",
    "https://member.bilibili.com/platform/upload/video/frame"
)
def select_bilibili_creation_statement(page) -> bool:
    """
    选择 B站创作声明：内容无需标注
    流程：
    1. 点击创作声明下拉框
    2. 点击“内容无需标注”
    """

    print("开始选择创作声明：内容无需标注")

    try:
        page.screenshot(
            path=str(BASE_DIR / "bilibili_before_creation_statement.png"),
            full_page=True
        )

        # 第一步：点击创作声明下拉框
        dropdown_clicked = False

        dropdown_selectors = [
            # 优先找“创作声明”所在容器
            "div:has-text('创作声明') .bcc-select",
            "div:has-text('创作声明') .bcc-select-input",
            "div:has-text('创作声明') .bcc-select-selection",
            "div:has-text('创作声明') [class*='select']",

            # 兜底：找页面里显示“请选择”的下拉框
            "div:has-text('创作声明') text=请选择",
            "div:has-text('创作声明') text=请选择类型",
            "div:has-text('创作声明') text=请选择声明",

            # 再兜底：所有 select 类组件
            ".bcc-select",
            "[class*='select']",
        ]

        for selector in dropdown_selectors:
            try:
                locator = page.locator(selector).first
                locator.wait_for(state="visible", timeout=5000)
                locator.click()
                page.wait_for_timeout(1200)

                print(f"已点击创作声明下拉框：{selector}")
                dropdown_clicked = True
                break
            except Exception:
                continue

        # 如果选择器点击失败，使用坐标点击：点击“创作声明”文字右侧
        if not dropdown_clicked:
            try:
                label = page.locator("text=创作声明").first
                label.wait_for(state="visible", timeout=5000)
                box = label.bounding_box()

                if box:
                    x = box["x"] + 220
                    y = box["y"] + box["height"] / 2
                    page.mouse.click(x, y)
                    page.wait_for_timeout(1200)

                    print("已通过坐标点击创作声明下拉框")
                    dropdown_clicked = True
            except Exception as e:
                print(f"坐标点击创作声明下拉框失败：{e}")

        if not dropdown_clicked:
            print("没有成功点击创作声明下拉框")
            page.screenshot(
                path=str(BASE_DIR / "bilibili_creation_dropdown_click_failed.png"),
                full_page=True
            )
            return False

        # 第二步：点击下拉选项“内容无需标注”
        option_clicked = False

        option_selectors = [
            "text=内容无需标注",
            "li:has-text('内容无需标注')",
            "div:has-text('内容无需标注')",
            "span:has-text('内容无需标注')",
            "[class*='option']:has-text('内容无需标注')",
            "[class*='item']:has-text('内容无需标注')",
        ]

        for selector in option_selectors:
            try:
                option = page.locator(selector).last
                option.wait_for(state="visible", timeout=5000)
                option.click()
                page.wait_for_timeout(1200)

                print(f"已选择创作声明选项：内容无需标注，selector={selector}")
                option_clicked = True
                break
            except Exception:
                continue

        if not option_clicked:
            print("下拉框已点击，但没有找到或没有点中“内容无需标注”")
            page.screenshot(
                path=str(BASE_DIR / "bilibili_creation_option_not_clicked.png"),
                full_page=True
            )
            return False

        # 第三步：截图确认
        page.screenshot(
            path=str(BASE_DIR / "bilibili_creation_statement_selected.png"),
            full_page=True
        )

        print("创作声明已选择：内容无需标注")
        return True

    except Exception as e:
        print(f"选择创作声明失败：{e}")
        page.screenshot(
            path=str(BASE_DIR / "bilibili_creation_statement_error.png"),
            full_page=True
        )
        return False

def load_tasks() -> List[Dict[str, Any]]:
    if not TASKS_FILE.exists():
        print(f"任务文件不存在：{TASKS_FILE}")
        return []

    tasks = []

    with TASKS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                tasks.append(json.loads(line))
            except Exception as e:
                print(f"跳过异常任务行：{e}")

    return tasks


def save_tasks(tasks: List[Dict[str, Any]]) -> None:
    with TASKS_FILE.open("w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")


def find_video_file(task: Dict[str, Any]) -> Optional[Path]:
    local_video_path = task.get("local_video_path")

    if local_video_path:
        p = Path(local_video_path)
        if p.exists() and p.is_file():
            return p

    output_dir = task.get("download_output_dir")

    if not output_dir:
        return None

    output_dir = Path(output_dir)

    if not output_dir.exists():
        return None

    candidates = []

    for ext in ["*.mp4", "*.mkv", "*.webm"]:
        candidates.extend(output_dir.rglob(ext))

    candidates = [
        p for p in candidates
        if p.is_file() and not str(p).endswith(".part")
    ]

    if not candidates:
        return None

    return max(candidates, key=lambda p: p.stat().st_mtime)


def build_title(task: Dict[str, Any]) -> str:
    """
    B站标题：
    优先使用 YouTube 原标题翻译后的中文标题。
    如果翻译失败，再回退到固定标题或原始标题。
    """
    from translate_title import translate_to_chinese

    source_title = (
        task.get("source_video_title")
        or task.get("download_title")
        or ""
    )

    if source_title:
        title = translate_to_chinese(source_title)
    else:
        title = (
            task.get("bilibili_title")
            or "国外趣味视频"
        )

    title = title.replace("\n", " ").strip()

    if len(title) > 70:
        title = title[:68] + "…"

    return title

def build_desc(task: Dict[str, Any]) -> str:
    source_title = task.get("source_video_title") or ""
    source_url = task.get("source_video_url") or ""
    channel_name = task.get("channel_name") or ""

    desc = f"""标题：{source_title}

来源频道：{channel_name}
来源链接：{source_url}
"""

    suffix = CONFIG.get("bilibili_desc_suffix", "")

    if suffix:
        desc += suffix

    return desc.strip()


def build_tags(task: Dict[str, Any]) -> List[str]:
    tags = []

    for tag in CONFIG.get("bilibili_default_tags", []):
        tag = str(tag).strip()
        if tag and tag not in tags:
            tags.append(tag)

    channel_name = task.get("channel_name")

    if channel_name and channel_name not in tags:
        tags.append(channel_name)

    return tags[:10]


def fill_first_available(page, selectors: List[str], value: str, timeout: int = 8000) -> bool:
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=timeout)
            locator.fill(value)
            return True
        except Exception:
            continue

    return False


def click_first_available(page, selectors: List[str], timeout: int = 5000) -> bool:
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=timeout)
            locator.click()
            return True
        except Exception:
            continue

    return False


def upload_one_task(page, task: Dict[str, Any]) -> bool:
    video_file = find_video_file(task)

    if not video_file:
        print("没有找到本地视频文件，跳过：")
        print(task.get("source_video_url"))
        return False

    title = build_title(task)
    desc = build_desc(task)
    tags = build_tags(task)

    print("=" * 60)
    print("开始上传 B站")
    print(f"视频文件：{video_file}")
    print(f"标题：{title}")
    print(f"标签：{tags}")
    print("=" * 60)

    page.goto(UPLOAD_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)

    # 如果登录态失效，保存截图
    if "login" in page.url.lower():
        page.screenshot(path=str(BASE_DIR / "bilibili_login_required.png"), full_page=True)
        print("B站登录态可能已失效，已保存截图：bilibili_login_required.png")
        return False

    # 找上传 input
    file_input = None

    possible_file_inputs = [
        "input[type='file']",
        "input.accept-video",
    ]

    for selector in possible_file_inputs:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="attached", timeout=15000)
            file_input = locator
            break
        except Exception:
            continue

    if not file_input:
        page.screenshot(path=str(BASE_DIR / "bilibili_upload_input_not_found.png"), full_page=True)
        print("没有找到上传 input，已保存截图：bilibili_upload_input_not_found.png")
        return False

    file_input.set_input_files(str(video_file))
    print("视频文件已提交，等待 B站处理...")

    # 视频上传和转码初始化需要时间
    page.wait_for_timeout(15000)

    # 填标题
    title_ok = fill_first_available(
        page,
        [
            "input[placeholder*='标题']",
            "textarea[placeholder*='标题']",
            "input[aria-label*='标题']",
            ".input-title input",
        ],
        title,
        timeout=12000,
    )

    print("标题填写完成" if title_ok else "标题输入框未找到")

    # 填简介
    desc_ok = fill_first_available(
        page,
        [
            "textarea[placeholder*='简介']",
            "textarea[placeholder*='描述']",
            "textarea[aria-label*='简介']",
            ".desc textarea",
        ],
        desc,
        timeout=8000,
    )

    print("简介填写完成" if desc_ok else "简介输入框未找到")

    # 填标签
    tag_count = 0

    for tag in tags:
        for selector in [
            "input[placeholder*='标签']",
            "input[placeholder*='按回车']",
            "input[aria-label*='标签']",
        ]:
            try:
                tag_input = page.locator(selector).first
                tag_input.wait_for(state="visible", timeout=3000)
                tag_input.fill(tag)
                page.keyboard.press("Enter")
                page.wait_for_timeout(500)
                tag_count += 1
                break
            except Exception:
                continue

    print(f"尝试填写标签数量：{tag_count}")

    # 截图留档
    page.screenshot(path=str(BASE_DIR / "bilibili_upload_filled.png"), full_page=True)

    auto_submit = CONFIG.get("bilibili_auto_submit", False)
    # 选择创作声明：无声明
    creation_statement_ok = select_bilibili_creation_statement(page)

    if creation_statement_ok:
        print("创作声明处理完成")
    else:
        print("创作声明未处理成功，后续可能无法发布")
    if not auto_submit:
        print("当前 bilibili_auto_submit=False，仅上传并填写信息，不自动发布。")
        return True

    submit_ok = click_first_available(
        page,
        [
            "text=立即投稿",
            "text=发布",
            "button:has-text('立即投稿')",
            "button:has-text('发布')",
        ],
        timeout=8000,
    )

    if submit_ok:
        print("已点击发布按钮，等待反馈...")
        page.wait_for_timeout(10000)
        page.screenshot(path=str(BASE_DIR / "bilibili_after_submit.png"), full_page=True)
        return True

    print("没有找到发布按钮。")
    page.screenshot(path=str(BASE_DIR / "bilibili_submit_not_found.png"), full_page=True)
    return False


def run_pending_uploads():
    result_summary = {
        "platform": "bilibili",
        "platform_name": "B站",
        "total": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "details": []
    }
    if not STATE_FILE.exists():
        print(f"找不到 B站登录态文件：{STATE_FILE}")
        print("请先在 Windows 本地运行 bilibili_login_export.py，然后上传 bilibili_state.json 到服务器。")
        return

    tasks = load_tasks()

    if not tasks:
        print("没有任务。")
        return

    pending_tasks = []

    for idx, task in enumerate(tasks):
        bili = task.get("platforms", {}).get("bilibili", {})

        if task.get("status") != "pending":
            continue

        if not bili.get("enabled", CONFIG.get("publish_to_bilibili", False)):
            continue

        if bili.get("status") not in [None, "pending", "failed"]:
            continue

        pending_tasks.append((idx, task))

    if not pending_tasks:
        print("没有待上传 B站的任务。")
        return
    result_summary["total"] = len(pending_tasks)
    print(f"待上传 B站任务数：{len(pending_tasks)}")

    headless = CONFIG.get("bilibili_headless", True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = browser.new_context(
            storage_state=str(STATE_FILE),
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        page = context.new_page()

        for idx, task in pending_tasks:
            try:
                success = upload_one_task(page, task)

                tasks[idx].setdefault("platforms", {}).setdefault("bilibili", {})

                if success:
                    tasks[idx]["platforms"]["bilibili"]["status"] = "uploaded_or_waiting_manual_submit"
                    tasks[idx]["platforms"]["bilibili"]["uploaded_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    print("B站任务状态已更新：uploaded_or_waiting_manual_submit")
                    result_summary["success"] += 1
                    result_summary["details"].append({
                        "title": task.get("source_video_title") or task.get("download_title"),
                        "channel_no": task.get("channel_no"),
                        "channel_name": task.get("channel_name"),
                        "source_url": task.get("source_video_url"),
                        "local_video_path": task.get("local_video_path"),
                        "status": tasks[idx]["platforms"]["bilibili"]["status"],
                        "message": "B站上传流程执行成功"
                    })
                else:
                    tasks[idx]["platforms"]["bilibili"]["status"] = "failed"
                    tasks[idx]["platforms"]["bilibili"]["error"] = "upload failed"
                    print("B站任务标记为失败")
                    result_summary["failed"] += 1
                    result_summary["details"].append({
                        "title": task.get("source_video_title") or task.get("download_title"),
                        "channel_no": task.get("channel_no"),
                        "channel_name": task.get("channel_name"),
                        "source_url": task.get("source_video_url"),
                        "local_video_path": task.get("local_video_path"),
                        "status": "failed",
                        "message": "B站上传失败"
                    })

                save_tasks(tasks)

            except Exception as e:
                print(f"B站上传异常：{e}")

                tasks[idx].setdefault("platforms", {}).setdefault("bilibili", {})
                tasks[idx]["platforms"]["bilibili"]["status"] = "failed"
                tasks[idx]["platforms"]["bilibili"]["error"] = str(e)
                save_tasks(tasks)
                result_summary["failed"] += 1
                result_summary["details"].append({
                    "title": task.get("source_video_title") or task.get("download_title"),
                    "channel_no": task.get("channel_no"),
                    "channel_name": task.get("channel_name"),
                    "source_url": task.get("source_video_url"),
                    "local_video_path": task.get("local_video_path"),
                    "status": "failed",
                    "message": str(e)
                })

        context.close()
        browser.close()

    print("B站上传任务处理完成。")
    return result_summary


if __name__ == "__main__":
    run_pending_uploads()