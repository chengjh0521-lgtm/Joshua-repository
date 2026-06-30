$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (!(Test-Path ".env")) {
  Write-Host "未发现 .env。请先执行：copy .env.example .env，然后手动修改配置。"
}

if (!(Test-Path ".venv")) {
  python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r apps\novel-writer-agent\requirements.txt

$env:PYTHONPATH = $Root
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
