# zhihu-writer-agent-deepseek-only

只使用 DeepSeek API 的知乎内容生成 MVP。当前不再自动打开知乎网页，不再自动输入到网站，不再自动发布。

生成结果会自动保存为 `.txt` 文件，并按日期和问题分目录存放。

目录结构类似：

```text
txt_outputs/
└── 2026-06-18/
    ├── 普通人如何用概率思维做理财决策/
    │   └── long_article.txt
    └── 普通人为什么总是高估短期收益/
        └── idea.txt
```

## 两条路线

1. 长文章路线：输入选题和期望字数，生成接近目标字数的长文章，保存为 `long_article.txt`。
2. 想法路线：输入选题，生成 400 到 900 字知乎想法，保存为 `idea.txt`。

## 安装

```bash
cd zhihu-writer-agent-deepseek-only
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

编辑 `.env`：

```env
DEEPSEEK_API_KEY=你的 DeepSeek API Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

## 启动

```bash
uvicorn backend.main:app --reload
```

打开接口文档：

```text

```

## 生成长文章 txt

接口：

```text
POST /api/articles/generate-draft
```

请求：

```json
{
  "topic": "普通人如何用概率思维做理财决策"
}
```

返回里看：

```json
{
  "status": "article_txt_saved",
  "text_path": "..."
}
```

兼容旧入口：

```text
POST /api/articles/generate
```

## 生成想法 txt

接口：

```text
POST /api/ideas/generate
```

请求：

```json
{
  "topic": "普通人为什么总是高估短期收益"
}
```

返回里看：

```json
{
  "status": "idea_txt_saved",
  "text_path": "..."
}
```

## 查看历史

```text
GET /api/articles
GET /api/articles/latest
GET /api/articles/{article_id}
```

## 说明

- 不再使用 Playwright 打开知乎网页。
- 不再自动填入知乎。
- 不再自动发布。
- 每个选题单独一个文件夹。
- 最外层用日期分文件夹。
- 同一天同一个选题重复生成时，同类型文件会覆盖旧文件。
- 如果当前 Windows 环境拒绝创建新文件夹，程序会退回到 `backend/data/articles/` 里保存带日期和选题名的 txt 文件。
