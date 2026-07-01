
# -*- coding: utf-8 -*-

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from playwright.sync_api import sync_playwright

from config import CONFIG


BASE_DIR = Path(__file__).resolve().parent
TASKS_FILE = Path(CONFIG["publish_tasks_file"])
STATE_FILE = Path(CONFIG["douyin_state_file"])
UPLOAD_URL = CONFIG.get(
    "douyin_upload_url",
    "https://creator.douyin.com/creator-micro/content/upload"
)
def click_douyin_publish_button(page) -> bool:
    """
    点击抖音底部真正的红色“发布”按钮。
    只点击可见、启用、靠近页面底部的 button。
    避免点到其他“发布”文字。
    """

    print("开始点击抖音底部发布按钮")

    try:
        page.screenshot(
            path=str(BASE_DIR / "douyin_before_publish_click.png"),
            full_page=True
        )

        # 滚动到底部，确保底部发布按钮可见
        page.mouse.wheel(0, 5000)
        page.wait_for_timeout(1500)

        # 只找 button，不再找 div/text
        buttons = page.locator("button:has-text('发布')")
        count = buttons.count()

        print(f"找到发布 button 数量：{count}")

        if count <= 0:
            page.screenshot(
                path=str(BASE_DIR / "douyin_publish_button_not_found.png"),
                full_page=True
            )
            print("没有找到 button:has-text('发布')")
            return False

        candidates = []

        viewport = page.viewport_size or {"width": 1440, "height": 900}
        viewport_height = viewport["height"]

        for i in range(count):
            try:
                btn = buttons.nth(i)

                if not btn.is_visible():
                    continue

                box = btn.bounding_box()

                if not box:
                    continue

                text = btn.inner_text(timeout=3000).strip()

                disabled = btn.get_attribute("disabled")
                aria_disabled = btn.get_attribute("aria-disabled")
                class_name = btn.get_attribute("class") or ""

                print(
                    f"发布按钮候选 {i}: text={text}, "
                    f"x={box['x']}, y={box['y']}, "
                    f"w={box['width']}, h={box['height']}, "
                    f"disabled={disabled}, aria_disabled={aria_disabled}, class={class_name}"
                )

                # 只要纯“发布”按钮
                if text != "发布":
                    continue

                # 排除禁用按钮
                if disabled is not None or aria_disabled == "true":
                    continue

                # 优先选择靠近页面底部的按钮
                candidates.append({
                    "index": i,
                    "button": btn,
                    "box": box,
                    "score": box["y"],
                })

            except Exception as e:
                print(f"检查发布按钮候选 {i} 异常：{e}")
                continue

        if not candidates:
            print("没有找到合适的底部发布按钮候选")
            page.screenshot(
                path=str(BASE_DIR / "douyin_publish_button_no_candidate.png"),
                full_page=True
            )
            return False

        # 选择 y 最大的，也就是最靠下的那个按钮
        candidates.sort(key=lambda x: x["score"], reverse=True)
        target = candidates[0]
        btn = target["button"]
        box = target["box"]

        print(
            f"准备点击发布按钮 index={target['index']} "
            f"x={box['x']}, y={box['y']}, w={box['width']}, h={box['height']}"
        )

        # 用坐标点击按钮中心，比 locator.click 更稳定
        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2

        page.mouse.click(x, y)
        page.wait_for_timeout(5000)

        page.screenshot(
            path=str(BASE_DIR / "douyin_after_publish_click.png"),
            full_page=True
        )

        print("已点击底部发布按钮")
        return True

    except Exception as e:
        print(f"点击抖音发布按钮异常：{e}")
        page.screenshot(
            path=str(BASE_DIR / "douyin_publish_click_error.png"),
            full_page=True
        )
        return False
def fill_douyin_title_and_desc(page, title: str, desc: str) -> bool:
    """
    抖音页面填写：
    1. 标题填入“填写作品标题，为作品获得更多流量”这个 0/30 的输入框
    2. 简介/话题填入下面的作品描述区域
    """

    print("开始填写抖音标题和简介")

    title_ok = False
    desc_ok = False

    # =========================
    # 1. 填写标题
    # =========================
    title_selectors = [
        "textarea[placeholder*='填写作品标题']",
        "input[placeholder*='填写作品标题']",
        "textarea[placeholder*='作品标题']",
        "input[placeholder*='作品标题']",
        "textarea[maxlength='30']",
        "input[maxlength='30']",
    ]

    for selector in title_selectors:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=8000)
            locator.click()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.keyboard.type(title, delay=20)
            page.wait_for_timeout(800)

            print(f"抖音标题填写完成：{selector}")
            title_ok = True
            break
        except Exception:
            continue

    if not title_ok:
        print("没有找到抖音标题输入框，尝试坐标兜底填写")

        try:
            # 通过“作品描述”标题定位右侧输入区域
            label = page.locator("text=作品描述").first
            label.wait_for(state="visible", timeout=5000)
            box = label.bounding_box()

            if box:
                # 标题输入框一般在“作品描述”文字右侧偏上
                x = box["x"] + 170
                y = box["y"] + 20

                page.mouse.click(x, y)
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                page.keyboard.type(title, delay=20)
                page.wait_for_timeout(800)

                print("抖音标题已通过坐标兜底填写")
                title_ok = True

        except Exception as e:
            print(f"标题坐标兜底填写失败：{e}")

    # =========================
    # 2. 填写简介 / 话题
    # =========================
    if desc:
        desc_selectors = [
            "textarea[placeholder*='添加话题']",
            "textarea[placeholder*='添加作品描述']",
            "textarea[placeholder*='描述']",
            "div[contenteditable='true']",
            "[contenteditable='true']",
        ]

        for selector in desc_selectors:
            try:
                locator = page.locator(selector).last
                locator.wait_for(state="visible", timeout=8000)

                # 避免又点回标题框
                locator.click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                page.keyboard.type(desc, delay=20)
                page.wait_for_timeout(800)

                print(f"抖音简介/话题填写完成：{selector}")
                desc_ok = True
                break
            except Exception:
                continue

        if not desc_ok:
            print("没有找到简介输入框，尝试坐标兜底填写")

            try:
                label = page.locator("text=作品描述").first
                label.wait_for(state="visible", timeout=5000)
                box = label.bounding_box()

                if box:
                    # 简介区域一般在标题输入框下面
                    x = box["x"] + 170
                    y = box["y"] + 80

                    page.mouse.click(x, y)
                    page.keyboard.press("Control+A")
                    page.keyboard.press("Backspace")
                    page.keyboard.type(desc, delay=20)
                    page.wait_for_timeout(800)

                    print("抖音简介已通过坐标兜底填写")
                    desc_ok = True

            except Exception as e:
                print(f"简介坐标兜底填写失败：{e}")
    else:
        print("简介为空，跳过简介填写")
        desc_ok = True

    page.screenshot(
        path=str(BASE_DIR / "douyin_title_desc_filled.png"),
        full_page=True
    )

    if not title_ok:
        print("抖音标题填写失败")
        return False

    return True
def load_tasks() -> List[Dict[str, Any]]:
    """
    读取 publish_tasks.jsonl。
    一行一个 JSON。
    """
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
    """
    重写 publish_tasks.jsonl。
    """
    with TASKS_FILE.open("w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")


def find_video_file(task: Dict[str, Any]) -> Optional[Path]:
    """
    优先使用 local_video_path。
    如果没有，就从 download_output_dir 里查找最新视频文件。
    """
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
    抖音标题：
    优先使用 YouTube 原标题翻译成中文。
    翻译失败时回退到原始标题。
    """
    source_title = (
        task.get("source_video_title")
        or task.get("download_title")
        or ""
    )

    try:
        from translate_title import translate_to_chinese

        if source_title:
            title = translate_to_chinese(source_title)
        else:
            title = "国外趣味视频"

    except Exception as e:
        print(f"标题翻译模块异常，使用原标题：{e}")
        title = source_title or "国外趣味视频"

    title = title.replace("\n", " ").strip()

    if len(title) > 55:
        title = title[:53] + "…"

    return title


def build_desc(task: Dict[str, Any]) -> str:
    return ""

def get_douyin_collection_name(task: Dict[str, Any]) -> Optional[str]:
    """
    获取当前任务对应的抖音合集名。

    优先级：
    1. publish_tasks.jsonl 里的 douyin_collection
    2. config.py 里的 douyin_collection_map[channel_no]
    3. 没有则跳过合集选择
    """
    collection = task.get("douyin_collection")

    if collection:
        return str(collection).strip()

    channel_no = task.get("channel_no")
    collection_map = CONFIG.get("douyin_collection_map", {})

    if channel_no and channel_no in collection_map:
        return str(collection_map[channel_no]).strip()

    return None


def fill_first_available(page, selectors: List[str], value: str, timeout: int = 8000) -> bool:
    """
    尝试填充多个可能的输入框。
    优先使用 click + Ctrl+A + type，避免某些网页 fill 后不触发前端事件。
    """
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=timeout)

            locator.click()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.keyboard.type(value, delay=20)

            return True
        except Exception:
            continue

    return False


def click_first_available(page, selectors: List[str], timeout: int = 5000) -> bool:
    """
    尝试点击多个可能的按钮。
    """
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=timeout)
            locator.click()
            return True
        except Exception:
            continue

    return False


def select_douyin_collection(page, task: Dict[str, Any]) -> bool:
    """
    选择抖音合集：
    1. 点击“请选择合集”下拉框
    2. 根据 channel_no / douyin_collection 选择对应合集
    3. 如果下拉选项找不到，尝试输入合集名搜索
    """

    collection_name = get_douyin_collection_name(task)

    if not collection_name:
        print("当前任务没有配置抖音合集，跳过合集选择。")
        return True

    print(f"开始选择抖音合集：{collection_name}")

    try:
        page.screenshot(
            path=str(BASE_DIR / "douyin_before_collection.png"),
            full_page=True
        )

        # =========================
        # 第一步：点击合集下拉框
        # =========================
        dropdown_clicked = False

        dropdown_selectors = [
            "text=请选择合集",
            "div:has-text('请选择合集')",
            "span:has-text('请选择合集')",
            "input[placeholder*='请选择合集']",
            "input[placeholder*='合集']",
            "div:has-text('添加合集') [class*='select']",
            "div:has-text('合集') [class*='select']",
            "div:has-text('合集')",
        ]

        for selector in dropdown_selectors:
            try:
                locator = page.locator(selector).first
                locator.wait_for(state="visible", timeout=8000)
                locator.click()
                page.wait_for_timeout(1500)

                print(f"已点击合集下拉框：{selector}")
                dropdown_clicked = True
                break
            except Exception:
                continue

        # 兜底：通过“请选择合集”坐标点击
        if not dropdown_clicked:
            try:
                label = page.locator("text=请选择合集").first
                label.wait_for(state="visible", timeout=5000)
                box = label.bounding_box()

                if box:
                    x = box["x"] + box["width"] / 2
                    y = box["y"] + box["height"] / 2
                    page.mouse.click(x, y)
                    page.wait_for_timeout(1500)

                    print("已通过坐标点击“请选择合集”下拉框")
                    dropdown_clicked = True
            except Exception as e:
                print(f"坐标点击“请选择合集”失败：{e}")

        if not dropdown_clicked:
            print("没有成功点击“请选择合集”下拉框")
            page.screenshot(
                path=str(BASE_DIR / "douyin_collection_dropdown_click_failed.png"),
                full_page=True
            )
            return False

        page.screenshot(
            path=str(BASE_DIR / "douyin_collection_dropdown_opened.png"),
            full_page=True
        )

        # =========================
        # 第二步：直接点击合集选项
        # =========================
        option_clicked = False

        option_selectors = [
            f"text={collection_name}",
            f"text='{collection_name}'",
            f"div:has-text('{collection_name}')",
            f"span:has-text('{collection_name}')",
            f"li:has-text('{collection_name}')",
            f"p:has-text('{collection_name}')",
            f"[class*='option']:has-text('{collection_name}')",
            f"[class*='item']:has-text('{collection_name}')",
            f"[role='option']:has-text('{collection_name}')",
            f"[role='menuitem']:has-text('{collection_name}')",
        ]

        for selector in option_selectors:
            try:
                option = page.locator(selector).last
                option.wait_for(state="visible", timeout=3000)
                option.click()
                page.wait_for_timeout(1200)

                print(f"已选择抖音合集：{collection_name}，selector={selector}")
                option_clicked = True
                break
            except Exception:
                continue

        if option_clicked:
            page.screenshot(
                path=str(BASE_DIR / "douyin_collection_selected.png"),
                full_page=True
            )
            return True

        # =========================
        # 第三步：如果直接找不到，尝试输入搜索合集名
        # =========================
        print(f"直接未找到合集：{collection_name}，开始尝试搜索输入")

        search_input_clicked = False

        search_input_selectors = [
            "input[placeholder*='搜索']",
            "input[placeholder*='合集']",
            "input",
            "[contenteditable='true']",
        ]

        for selector in search_input_selectors:
            try:
                inp = page.locator(selector).last
                inp.wait_for(state="visible", timeout=5000)
                inp.click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                page.keyboard.type(collection_name, delay=50)
                page.wait_for_timeout(2000)

                print(f"已输入合集搜索词：{collection_name}，selector={selector}")
                search_input_clicked = True
                break
            except Exception:
                continue

        if not search_input_clicked:
            print("没有找到合集搜索输入框")
            page.screenshot(
                path=str(BASE_DIR / "douyin_collection_search_input_not_found.png"),
                full_page=True
            )
            return False

        page.screenshot(
            path=str(BASE_DIR / "douyin_collection_after_search.png"),
            full_page=True
        )

        # =========================
        # 第四步：点击搜索结果
        # =========================
        for selector in option_selectors:
            try:
                option = page.locator(selector).last
                option.wait_for(state="visible", timeout=5000)
                option.click()
                page.wait_for_timeout(1200)

                print(f"已从搜索结果选择抖音合集：{collection_name}，selector={selector}")
                page.screenshot(
                    path=str(BASE_DIR / "douyin_collection_selected.png"),
                    full_page=True
                )
                return True
            except Exception:
                continue

        print(f"搜索后仍未找到合集：{collection_name}")
        page.screenshot(
            path=str(BASE_DIR / "douyin_collection_option_not_found.png"),
            full_page=True
        )
        return False

    except Exception as e:
        print(f"选择抖音合集失败：{e}")
        page.screenshot(
            path=str(BASE_DIR / "douyin_collection_error.png"),
            full_page=True
        )
        return False


def select_douyin_first_frame_cover(page) -> bool:
    """
    选择抖音封面：第一帧。
    如果没有找到封面设置入口，默认跳过，不阻断上传。
    """
    print("开始设置封面：第一帧")

    try:
        page.screenshot(
            path=str(BASE_DIR / "douyin_before_cover.png"),
            full_page=True
        )

        cover_entry_clicked = False

        cover_entry_selectors = [
            "text=选择封面",
            "text=编辑封面",
            "text=设置封面",
            "button:has-text('选择封面')",
            "button:has-text('编辑封面')",
            "button:has-text('设置封面')",
            "div:has-text('选择封面')",
            "div:has-text('编辑封面')",
            "div:has-text('设置封面')",
        ]

        for selector in cover_entry_selectors:
            try:
                locator = page.locator(selector).first
                locator.wait_for(state="visible", timeout=8000)
                locator.click()
                page.wait_for_timeout(2000)
                print(f"已打开封面设置：{selector}")
                cover_entry_clicked = True
                break
            except Exception:
                continue

        if not cover_entry_clicked:
            print("没有找到封面设置入口，可能页面默认已使用第一帧，跳过。")
            page.screenshot(
                path=str(BASE_DIR / "douyin_cover_entry_not_found.png"),
                full_page=True
            )
            return True

        first_frame_clicked = False

        first_frame_selectors = [
            "text=第一帧",
            "text=视频第一帧",
            "div:has-text('第一帧')",
            "span:has-text('第一帧')",
            "button:has-text('第一帧')",
        ]

        for selector in first_frame_selectors:
            try:
                locator = page.locator(selector).first
                locator.wait_for(state="visible", timeout=5000)
                locator.click()
                page.wait_for_timeout(1000)
                print(f"已选择第一帧封面：{selector}")
                first_frame_clicked = True
                break
            except Exception:
                continue

        # 如果没有明确“第一帧”按钮，尝试点第一个缩略图
        if not first_frame_clicked:
            thumbnail_selectors = [
                "[class*='cover'] img",
                "[class*='thumb'] img",
                "[class*='poster'] img",
                "img",
                "canvas",
            ]

            for selector in thumbnail_selectors:
                try:
                    locator = page.locator(selector).first
                    locator.wait_for(state="visible", timeout=5000)
                    locator.click()
                    page.wait_for_timeout(1000)
                    print("已尝试点击第一个封面缩略图作为第一帧")
                    first_frame_clicked = True
                    break
                except Exception:
                    continue

        if not first_frame_clicked:
            print("没有找到第一帧封面选项")
            page.screenshot(
                path=str(BASE_DIR / "douyin_first_frame_not_found.png"),
                full_page=True
            )
            return False

        confirm_clicked = False

        confirm_selectors = [
            "text=确定",
            "text=完成",
            "text=保存",
            "button:has-text('确定')",
            "button:has-text('完成')",
            "button:has-text('保存')",
        ]

        for selector in confirm_selectors:
            try:
                locator = page.locator(selector).last
                locator.wait_for(state="visible", timeout=5000)
                locator.click()
                page.wait_for_timeout(1500)
                print(f"封面设置已确认：{selector}")
                confirm_clicked = True
                break
            except Exception:
                continue

        if not confirm_clicked:
            print("没有找到封面确认按钮，可能已自动保存。")

        page.screenshot(
            path=str(BASE_DIR / "douyin_cover_selected.png"),
            full_page=True
        )

        return True

    except Exception as e:
        print(f"设置第一帧封面失败：{e}")
        page.screenshot(
            path=str(BASE_DIR / "douyin_cover_error.png"),
            full_page=True
        )
        return False


def upload_one_task(page, task: Dict[str, Any]) -> bool:
    """
    上传一个任务到抖音。
    """
    video_file = find_video_file(task)

    if not video_file:
        print("没有找到本地视频文件，跳过：")
        print(task.get("source_video_url"))
        return False

    title = build_title(task)
    desc = build_desc(task)

    print("=" * 60)
    print("开始上传抖音")
    print(f"视频文件：{video_file}")
    print(f"标题：{title}")
    print(f"频道编号：{task.get('channel_no')}")
    print(f"目标合集：{get_douyin_collection_name(task)}")
    print("=" * 60)

    page.goto(UPLOAD_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(8000)

    current_url = page.url.lower()

    if "login" in current_url or "passport" in current_url:
        page.screenshot(
            path=str(BASE_DIR / "douyin_login_required.png"),
            full_page=True
        )
        print("抖音登录态可能已失效，已保存截图：douyin_login_required.png")
        return False

    # 找上传 input
    file_input = None

    possible_file_inputs = [
        "input[type='file']",
        "input[accept*='video']",
        "input[accept*='mp4']",
    ]

    for selector in possible_file_inputs:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="attached", timeout=20000)
            file_input = locator
            break
        except Exception:
            continue

    if not file_input:
        page.screenshot(
            path=str(BASE_DIR / "douyin_upload_input_not_found.png"),
            full_page=True
        )
        print("没有找到抖音上传 input，已保存截图：douyin_upload_input_not_found.png")
        return False

    file_input.set_input_files(str(video_file))
    print("视频文件已提交，等待抖音处理...")

    # 等待上传初始化
    page.wait_for_timeout(20000)

    # 填描述
    # 填写抖音作品描述
    # 抖音这里没有独立标题框，作品描述第一行就是标题区域
    # 分别填写标题和简介
    title_desc_ok = fill_douyin_title_and_desc(page, title, desc)

    if title_desc_ok:
        print("抖音标题/简介填写完成")
    else:
        print("抖音标题/简介填写失败，停止发布")
        page.screenshot(
            path=str(BASE_DIR / "douyin_title_desc_failed_stop.png"),
            full_page=True
        )
        return False

    # 选择合集
    collection_ok = select_douyin_collection(page, task)

    if collection_ok:
        print("抖音合集选择完成")
    else:
        print("抖音合集选择失败，停止发布，避免误投")
        page.screenshot(
            path=str(BASE_DIR / "douyin_collection_failed_stop.png"),
            full_page=True
        )
        return False

    # 设置封面为第一帧


    # 发布前截图
    page.screenshot(
        path=str(BASE_DIR / "douyin_upload_filled.png"),
        full_page=True
    )

    auto_submit = CONFIG.get("douyin_auto_submit", False)

    if not auto_submit:
        print("当前 douyin_auto_submit=False，仅上传并填写信息，不自动发布。")
        return True

    # 等待一下，给抖音页面完成上传/处理/按钮激活的时间
    page.wait_for_timeout(10000)

    # 调用你新写的发布按钮点击函数
    submit_ok = click_douyin_publish_button(page)

    if submit_ok:
        print("已点击抖音发布按钮。")
        page.wait_for_timeout(10000)
        page.screenshot(
            path=str(BASE_DIR / "douyin_after_submit.png"),
            full_page=True
        )
        return True

    print("没有成功点击抖音发布按钮。")
    page.screenshot(
        path=str(BASE_DIR / "douyin_submit_not_found.png"),
        full_page=True
    )
    return False

def run_pending_uploads():
    """
    扫描 publish_tasks.jsonl 里的 pending 抖音任务并上传。
    每个任务单独启动浏览器，完成后立即关闭，避免 Chromium 长时间运行导致页面崩溃。
    """

    result_summary = {
        "platform": "douyin",
        "platform_name": "抖音",
        "total": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "details": []
    }

    if not STATE_FILE.exists():
        print(f"找不到抖音登录态文件：{STATE_FILE}")
        print("请先在 Windows 本地运行 douyin_login_export.py，然后上传 douyin_state.json 到服务器。")
        return result_summary

    tasks = load_tasks()

    if not tasks:
        print("没有任务。")
        return result_summary

    pending_tasks = []

    for idx, task in enumerate(tasks):
        douyin = task.get("platforms", {}).get("douyin", {})

        if task.get("status") != "pending":
            continue

        if not douyin.get("enabled", CONFIG.get("publish_to_douyin", False)):
            continue

        if douyin.get("status") not in [None, "pending", "failed"]:
            continue

        pending_tasks.append((idx, task))

    if not pending_tasks:
        print("没有待上传抖音的任务。")
        return result_summary

    result_summary["total"] = len(pending_tasks)

    print(f"待上传抖音任务数：{len(pending_tasks)}")

    headless = CONFIG.get("douyin_headless", True)

    with sync_playwright() as p:
        for idx, task in pending_tasks:
            browser = None
            context = None

            try:
                print("=" * 60)
                print(f"开始处理抖音任务：{idx}")
                print(f"频道：{task.get('channel_no')} / {task.get('channel_name')}")
                print(f"标题：{task.get('source_video_title') or task.get('download_title')}")
                print("=" * 60)

                browser = p.chromium.launch(
                    headless=headless,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-software-rasterizer",
                        "--disable-extensions",
                        "--disable-background-networking",
                        "--disable-background-timer-throttling",
                        "--disable-renderer-backgrounding",
                        "--disable-features=Translate,BackForwardCache,AcceptCHFrame,MediaRouter,OptimizationHints",
                        "--disable-blink-features=AutomationControlled",
                        "--mute-audio",
                        "--window-size=1440,900",
                    ],
                )

                context = browser.new_context(
                    storage_state=str(STATE_FILE),
                    viewport={"width": 1440, "height": 900},
                    device_scale_factor=1,
                    reduced_motion="reduce",
                    user_agent=(
                        "Mozilla/5.0 (X11; Linux x86_64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                )

                page = context.new_page()

                success = upload_one_task(page, task)

                tasks[idx].setdefault("platforms", {}).setdefault("douyin", {})

                if success:
                    if CONFIG.get("douyin_auto_submit", False):
                        tasks[idx]["platforms"]["douyin"]["status"] = "submit_clicked"
                    else:
                        tasks[idx]["platforms"]["douyin"]["status"] = "filled_waiting_manual_submit"

                    tasks[idx]["platforms"]["douyin"]["uploaded_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

                    print("抖音任务状态已更新：成功")

                    result_summary["success"] += 1
                    result_summary["details"].append({
                        "title": task.get("source_video_title") or task.get("download_title"),
                        "channel_no": task.get("channel_no"),
                        "channel_name": task.get("channel_name"),
                        "source_url": task.get("source_video_url"),
                        "local_video_path": task.get("local_video_path"),
                        "status": tasks[idx]["platforms"]["douyin"]["status"],
                        "message": "抖音上传流程执行完成"
                    })

                else:
                    tasks[idx]["platforms"]["douyin"]["status"] = "failed"
                    tasks[idx]["platforms"]["douyin"]["error"] = "upload or publish failed"

                    print("抖音任务标记为失败")

                    result_summary["failed"] += 1
                    result_summary["details"].append({
                        "title": task.get("source_video_title") or task.get("download_title"),
                        "channel_no": task.get("channel_no"),
                        "channel_name": task.get("channel_name"),
                        "source_url": task.get("source_video_url"),
                        "local_video_path": task.get("local_video_path"),
                        "status": "failed",
                        "message": "抖音上传失败"
                    })

                save_tasks(tasks)

            except Exception as e:
                print(f"抖音上传异常：{e}")

                tasks[idx].setdefault("platforms", {}).setdefault("douyin", {})
                tasks[idx]["platforms"]["douyin"]["status"] = "failed"
                tasks[idx]["platforms"]["douyin"]["error"] = str(e)

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

            finally:
                # 每个任务完成后，强制关闭页面上下文和浏览器
                try:
                    if context:
                        context.close()
                        print("已关闭 Playwright context")
                except Exception as e:
                    print(f"关闭 context 失败：{e}")

                try:
                    if browser:
                        browser.close()
                        print("已关闭 Chromium 浏览器")
                except Exception as e:
                    print(f"关闭 browser 失败：{e}")

                # 额外清理残留 Chromium 进程
                try:
                    import subprocess
                    subprocess.run(
                        "pkill -f 'chromium|chrome|playwright' || true",
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    print("已尝试清理残留 Chromium 进程")
                except Exception as e:
                    print(f"清理 Chromium 进程失败：{e}")

                # 每个任务之间休息一下，降低抖音风控和浏览器崩溃概率
                time.sleep(8)

    print("抖音上传任务处理完成。")
    return result_summary


if __name__ == "__main__":
    run_pending_uploads()

