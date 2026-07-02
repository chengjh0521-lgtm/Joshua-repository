# novel-writer-agent

一个只使用 DeepSeek API 的交互式本地小说创作 Agent。它不会一次性生成整本小说，而是每次根据历史记忆和用户新要求只生成一章。

## 功能

- 读取用户手动整理的番茄热门作品公开资料
- 只分析榜单、书名、简介、题材、标签、读者看点，不抓取正文
- 提炼抽象爆款共性，并生成原创性规则
- 生成原创小说大框架和本地记忆
- 每次只规划、生成、审稿、改写、检查并保存一章
- clean 文件只保存正文
- with_notes 文件保存正文、审稿意见、改写说明、原创性检查、本章摘要、人物状态更新、伏笔更新、下一章钩子
- 章节文件名自动清理 Windows 不允许的特殊字符

## 安装

```bash
cd novel-writer-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

编辑 `.env`：

```env
DEEPSEEK_API_KEY=你的 DeepSeek API Key
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

## 使用流程

### 直达生成

现在可以用 `python main` 直接生成内容：

```bash
python main 长篇 "承接上一章，推进调查并让主角付出代价"
```

```bash
python main 短篇 "写一个发生在雨夜便利店的悬疑短篇，结尾反转但要合情合理"
```

必选参数：

- `长篇` 或 `短篇`
- 生成内容描述

可选参数：

```bash
--max-words 3000
--min-words 100
--max-paragraphs 4
--remove-ai
--send-email
--email-to someone@example.com
```

示例：

```bash
python main 短篇 "一名夜班司机接到来自十年前的订单" --min-words 800 --max-words 3000 --max-paragraphs 4 --remove-ai
```

发送邮件：

```bash
python main 短篇 "写一个都市奇谈短篇" --send-email --email-to receiver@example.com
```

启用邮件发送前，先编辑 `email_config.json`：

```json
{
  "smtp_host": "smtp.qq.com",
  "smtp_port": 465,
  "sender_email": "你的QQ邮箱@qq.com",
  "authorization_code": "你的QQ邮箱授权码"
}
```

只有使用 `--send-email` 时，`--email-to` 才有效；一旦使用 `--send-email`，`--email-to` 必填。

### 原有流程

初始化目录和记忆文件：

```bash
python main.py init
```

手动整理 `data/fanqie_top10.txt`，只放公开资料，不要粘贴小说正文。

生成市场调研报告：

```bash
python main.py research --input data/fanqie_top10.txt
```

提炼共性与原创性规则：

```bash
python main.py extract
```

生成原创小说大框架：

```bash
python main.py build --genre "悬疑爽文" --style "番茄爆款节奏"
```

生成下一章：

```bash
python main.py write --goal "写开篇，主角卷入第一起异常事件，结尾留下强悬念"
```

长篇章节会进入编辑部循环：

```text
Reviewer
↓
Humanizer
↓
Continuity
↓
Boredom Editor
↓
Editor Gate
↓
Slow Reader
```

`Boredom Editor` 会检查这一章是不是每一分钟都在推进剧情。如果整章缺少无效动作、无效对白、无效观察、无效情绪等呼吸感，会 REJECT 并退回 Humanizer。

`next` 是 `write` 的别名：

```bash
python main.py next --goal "承接上一章，推进调查并让主角付出代价"
```

生成一个独立短篇小说，不更新长篇记忆：

```bash
python main.py short --goal "写一个发生在雨夜便利店的悬疑短篇，结尾反转但要合情合理"
```

也可以指定类型、风格和目标字数：

```bash
python main.py short --genre "都市奇谈" --style "冷静克制，结尾有余味" --words 3000 --goal "一名夜班司机接到来自十年前的订单"
```

把 txt 文本转换为指定总时长的 SRT 字幕：

```bash
python main.py subtitle --input output/short_stories/短篇_示例.txt --duration 03:00
```

指定输出路径和每条字幕最大字数：

```bash
python main.py subtitle --input input.txt --duration 00:05:30 --output output/subtitles/demo.srt --max-chars 22
```

字幕正文会始终保持单行；如果字幕太长，请调小 `--max-chars`。
字幕正文会清理标点，只保留中文句号 `。` 和中文逗号 `，`。

查看状态：

```bash
python main.py status
```

## 输出位置

- 正文：`output/chapters_clean/第001章_章节标题.txt`
- 带备注版本：`output/chapters_with_notes/第001章_章节标题.txt`
- 独立短篇正文：`output/short_stories/短篇_时间戳_短篇标题.txt`
- 独立短篇带备注版本：`output/short_stories_with_notes/短篇_时间戳_短篇标题.txt`
- 字幕文件：`output/subtitles/文本名_时长.srt`
- 记忆文件：`novel_memory/`

## 注意

本项目不做自动发布，不抓取小说正文，不使用 OpenAI API。调研环节依赖用户手动整理的公开资料。
