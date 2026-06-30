# Ubuntu 24.04 部署笔记

## 首次部署

```bash
sudo apt update
sudo apt install -y git docker.io docker-compose-plugin
sudo systemctl enable --now docker

git clone <你的私有仓库地址> ai-platform
cd ai-platform
cp .env.example .env
nano .env
docker compose up -d --build
```

浏览器访问：

```text
http://服务器IP:521
```

## 更新部署

```bash
cd ai-platform
git pull
docker compose up -d --build
```

## 注意

- 不要提交 `.env`。
- 不要提交 API Key。
- 不要提交 `apps/novel-writer-agent/output/` 生成内容。
- 不要提交 `apps/novel-writer-agent/novel_memory/` 长篇记忆。
