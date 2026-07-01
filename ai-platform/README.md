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

SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your_email_username
SMTP_PASSWORD=your_email_password_or_app_password
SMTP_FROM=your_email@example.com
SMTP_USE_TLS=true
SMTP_USE_SSL=false
```

开发阶段建议保留 `NOVEL_AGENT_MOCK=true`，这样 Agent 会生成本地测试文本，不消耗 DeepSeek Token。需要真实调用 DeepSeek 时，填写真实 Key，并设置 `NOVEL_AGENT_MOCK=false`。

如果需要“生成后发送 txt 到邮箱”，请配置 SMTP。常见邮箱需要使用“应用专用密码”，不要直接填写网页登录密码。

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
python main.py short --min-words 1800 --max-words 2500 --de-ai --style "冷静克制，结尾有余味" --goal "一名夜班司机接到来自十年前的订单"
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

### 邮件提示 Connection unexpectedly closed

通常是 SMTP 端口和加密方式不匹配。

465 端口通常这样配：

```env
SMTP_PORT=465
SMTP_USE_SSL=true
SMTP_USE_TLS=false
```

587 端口通常这样配：

```env
SMTP_PORT=587
SMTP_USE_SSL=false
SMTP_USE_TLS=true
```

同时确认 `SMTP_PASSWORD` 使用的是邮箱授权码或应用专用密码，不是网页登录密码。

### JSON 账户和试用额度

当前 MVP 使用 `backend/data/accounts.json` 保存可登录账户和体验额度。首次启动时，如果该文件不存在，系统会从 `backend/data/accounts.seed.json` 自动生成。

内置试用账号：

```text
用户名：test01
密码：test01
额度：5 次成功生成
```

额度规则：

- `generate`、`short`、`write`、`next` 这类会消耗 Token 的操作会检查额度。
- 只有生成成功，才扣 1 次。
- `status`、`init` 不扣次数。
- 管理员账号 `quota_limit` 为 `null`，不限制次数。

真实运行文件 `backend/data/accounts.json` 已被 `.gitignore` 忽略，避免服务器扣次数后影响 `git pull`。后续可以把这层替换成数据库。

### 视频监管发布 Agent

已接入 `apps/video-publisher-agent`，用于对接 YouTube 监管、下载和发布流程。网页右上角圆形账户按钮里可以配置：

- 邮件收件箱
- B站登录态 JSON
- 抖音登录态 JSON
- YouTube `cookies.txt`
- 是否下载后自动发布
- 是否发布到 B站/抖音

运行态配置和上传文件保存在 `backend/data/users/`，该目录已被 `.gitignore` 忽略，不会提交到 GitHub。

网页支持的视频 Agent 操作：

- `status`：检查配置和登录态文件是否存在
- `check-once`：执行一轮 YouTube 监管、下载和可选发布
- `upload-pending`：执行已有待发布任务

注意：B站/抖音发布依赖 Playwright 浏览器。默认 Docker 构建不会安装 Chromium，以免服务器网络、系统源或磁盘问题阻塞网站部署。只需要查看网页、生成小说、检查配置或下载流程时，直接运行：

```bash
docker compose build --no-cache
```

若要在容器内执行 B站/抖音发布，再使用：

```bash
docker compose build --no-cache --build-arg INSTALL_PLAYWRIGHT_BROWSERS=true
```

### 知乎写作 Agent

已接入 `apps/zhihu-writer-agent`，网页左侧选择“知乎写作 Agent”后可生成：

- 知乎长文
- 知乎想法

该 Agent 使用 `DEEPSEEK_API_KEY`，请在 `.env` 中配置：

```env
DEEPSEEK_API_KEY=你的 DeepSeek API Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

生成结果会保存到 `apps/zhihu-writer-agent/txt_outputs/`，运行数据库保存在 `apps/zhihu-writer-agent/backend/data/`。这两个目录已被 `.gitignore` 忽略，并在 `docker-compose.yml` 中挂载持久化。
