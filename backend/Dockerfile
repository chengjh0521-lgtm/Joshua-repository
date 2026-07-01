FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

COPY backend/requirements.txt /tmp/backend-requirements.txt
COPY apps/novel-writer-agent/requirements.txt /tmp/agent-requirements.txt
COPY apps/video-publisher-agent/requirements.txt /tmp/video-agent-requirements.txt

RUN pip install --no-cache-dir -r /tmp/backend-requirements.txt
RUN pip install --no-cache-dir -r /tmp/agent-requirements.txt
RUN pip install --no-cache-dir -r /tmp/video-agent-requirements.txt

ARG INSTALL_PLAYWRIGHT_BROWSERS=false
RUN if [ "$INSTALL_PLAYWRIGHT_BROWSERS" = "true" ]; then \
      python -m playwright install --with-deps chromium; \
    fi

COPY backend /app/backend
COPY apps /app/apps

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
