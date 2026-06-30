# AI 创作平台

这是一个本地开发、服务器部署的 AI 创作平台 MVP。第一阶段只接入小说创作 Agent，首页公开可访问，所有会消耗 AI Token 的操作都需要先登录。

技术栈：Python 3.11+、FastAPI、Jinja2、Cookie Session、本地文件存储、Docker、docker compose。第一版不引入 Vue、React、Redis、PostgreSQL、Celery。

## 本地开发方式

Windows PowerShell：

```powershell
cd ai-platform
copy .env.example .env
notepad .env
.\scripts\dev.ps1
```

打开：

```text
http://127.0.0.1:8000
```

也可以手动启动：

```powershell
cd ai-platform
python -m venv .venv
.\.venv\Scripts\activate
pip install -r backend\requirements.txt
pip install -r apps\novel-writer-agent\requirements.txt
$env:PYTHONPATH = (Get-Location).Path
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

## 环境变量配置

复制示例文件：

```powershell
copy .env.example .env
```

`.env` 示例：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
NOVEL_AGENT_MOCK=true

APP_SECRET_KEY=change_this_secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_this_password
```

开发阶段建议保留 `NOVEL_AGENT_MOCK=true`，这样 Agent 会生成本地测试文本，不消耗 DeepSeek Token。需要真实调用 DeepSeek 时，填写真实 Key，并设置 `NOVEL_AGENT_MOCK=false`。

## Docker 启动方式

```bash
cd ai-platform
cp .env.example .env
nano .env
docker compose up -d --build
```

访问：

```text
http://服务器IP:521
```

`docker-compose.yml` 会挂载以下目录，保证输出和记忆持久化：

- `apps/novel-writer-agent/output`
- `apps/novel-writer-agent/novel_memory`
- `apps/novel-writer-agent/data`

## GitHub 推送建议

```powershell
cd ai-platform
git init
git add .
git commit -m "Initial AI platform MVP"
git branch -M main
git remote add origin git@github.com:<你的账号>/<你的私有仓库>.git
git push -u origin main
```

提交前确认：

```powershell
git status --short
```

不要提交 `.env`、API Key、生成内容、长篇记忆、虚拟环境。

## 服务器部署方式

Ubuntu 24.04：

```bash
sudo apt update
sudo apt install -y git docker.io docker-compose-plugin
sudo systemctl enable --now docker

git clone git@github.com:<你的账号>/<你的私有仓库>.git ai-platform
cd ai-platform
cp .env.example .env
nano .env
docker compose up -d --build
```

后续更新：

```bash
cd ai-platform
git pull
docker compose up -d --build
```

## 登录系统说明

当前是单管理员登录，配置来自 `.env`：

- `APP_SECRET_KEY`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`

接口：

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

小说 Agent 的执行接口 `POST /api/novel/run` 和文件接口默认要求登录。

## 小说 Agent 使用说明

进入目录：

```powershell
cd ai-platform\apps\novel-writer-agent
```

常用命令：

```powershell
python main.py init
python main.py status
python main.py research --input data/fanqie_top10.txt
python main.py extract
python main.py build --genre "悬疑爽文" --style "番茄爆款节奏"
python main.py write --goal "写开篇，主角卷入第一起异常事件，结尾留下强悬念"
python main.py next --goal "承接上一章，推进调查并让主角付出代价"
python main.py short --goal "写一个发生在雨夜便利店的悬疑短篇，结尾反转但要合情合理"
python main.py short --genre "都市奇谈" --style "冷静克制，结尾有余味" --words 3000 --goal "一名夜班司机接到来自十年前的订单"
```

输出目录：

- `output/chapters_clean/`
- `output/chapters_with_notes/`
- `output/short_stories/`
- `output/short_stories_with_notes/`
- `novel_memory/`

## 注意事项

- 不要提交 `.env`。
- 不要提交 API Key。
- 不要提交生成内容。
- 不要抓取小说正文。
- 市场调研只读取用户手动整理的公开资料，例如榜单、书名、简介、题材、标签、读者看点。
- 提炼抽象共性，禁止抄袭具体人物、桥段、台词、设定和世界观。

## 常见问题排查

### 登录失败

检查 `.env` 中的 `ADMIN_USERNAME` 和 `ADMIN_PASSWORD`，重启后端。

### 页面能打开但执行 Agent 报错

先在命令行验证：

```powershell
cd ai-platform\apps\novel-writer-agent
python main.py status
python main.py short --goal "测试短篇生成"
```

### Docker 启动后访问不到

检查容器状态：

```bash
docker compose ps
docker compose logs -f
```

确认服务器安全组或防火墙放行 `521` 端口。

### 不想消耗 DeepSeek Token

保持：

```env
NOVEL_AGENT_MOCK=true
```

### 需要真实调用 DeepSeek

设置：

```env
DEEPSEEK_API_KEY=真实密钥
NOVEL_AGENT_MOCK=false
```
