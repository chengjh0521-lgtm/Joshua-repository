# -*- coding: utf-8 -*-

import re
from deep_translator import GoogleTranslator


def clean_title(title: str) -> str:
    """
    清洗 YouTube 标题：
    1. 去掉多余换行
    2. 去掉过多 hashtag
    3. 控制长度
    """

    if not title:
        return "国外趣味视频"

    title = title.replace("\n", " ").strip()

    # 去掉连续空格
    title = re.sub(r"\s+", " ", title)

    # 去掉 hashtag
    title = re.sub(r"#\w+", "", title).strip()

    return title


def translate_to_chinese(title: str) -> str:
    """
    把 YouTube 标题翻译成中文。
    翻译失败时回退到原文。
    """

    title = clean_title(title)

    if not title:
        return "国外趣味视频"

    try:
        zh_title = GoogleTranslator(source="auto", target="zh-CN").translate(title)

        if not zh_title:
            return title

        zh_title = zh_title.replace("\n", " ").strip()
        zh_title = re.sub(r"\s+", " ", zh_title)

        # B站标题长度控制，保守一点
        if len(zh_title) > 70:
            zh_title = zh_title[:68] + "…"

        return zh_title

    except Exception as e:
        print(f"标题翻译失败，使用原标题：{e}")

        if len(title) > 70:
            title = title[:68] + "…"

        return title