FROM node:24-bookworm-slim AS media
WORKDIR /srv
COPY apps/api/tools/media/package*.json ./
COPY apps/api/tools/media/prepare.cjs ./
RUN npm ci --omit=dev

FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-vie \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY apps/api/requirements.txt apps/api/requirements.txt
RUN python -m pip install --no-cache-dir -r apps/api/requirements.txt

COPY .claude/skills .claude/skills
COPY prompts prompts
COPY apps/api/app apps/api/app
COPY apps/api/tools/media/worker.cjs apps/api/tools/media/
COPY --from=media /usr/local/bin/node /usr/local/bin/node
COPY --from=media /srv/node_modules apps/api/tools/media/node_modules
RUN useradd --system --create-home tkc && mkdir -p /data && chown tkc:tkc /data
WORKDIR /srv/apps/api
USER tkc
EXPOSE 8000
CMD ["sh", "-c", "exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-access-log"]
