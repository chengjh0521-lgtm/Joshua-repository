# novel-writer-agent

本目录是 AI 创作平台第一阶段接入的小说创作 Agent。

默认情况下，Agent 使用本地 mock 文本生成，用于开发和流程测试，不会调用 DeepSeek API。需要真实调用时，在项目根目录 `.env` 中配置 DeepSeek，并设置：

```env
NOVEL_AGENT_MOCK=false
```

## 常用命令

```powershell
python main.py init
python main.py status
python main.py research --input data/fanqie_top10.txt
python main.py extract
python main.py build --genre "悬疑爽文" --style "番茄爆款节奏"
python main.py write --goal "写开篇，主角卷入第一起异常事件，结尾留下强悬念"
python main.py next --goal "承接上一章，推进调查并让主角付出代价"
python main.py short --goal "写一个发生在雨夜便利店的悬疑短篇，结尾反转但要合情合理"
```

## 输出目录

- `output/chapters_clean/`
- `output/chapters_with_notes/`
- `output/short_stories/`
- `output/short_stories_with_notes/`
- `novel_memory/`

`short` 不会更新长篇记忆；`write` 和 `next` 会更新 `novel_memory/`。
