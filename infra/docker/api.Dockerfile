FROM node:24-bookworm-slim AS media
WORKDIR /srv
COPY apps/api/tools/media/package*.json ./
COPY apps/api/tools/media/prepare.cjs ./
RUN npm ci --omit=dev

FROM python:3.12-slim-bookworm AS runtime

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

FROM debian:bookworm-slim AS whisper-build
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates git cmake g++ make \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git clone --depth 1 --branch v1.9.6 https://github.com/ggml-org/whisper.cpp.git whisper
RUN cmake -S whisper -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
    -DGGML_NATIVE=OFF -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_EXAMPLES=ON \
    && cmake --build build --target whisper-cli --parallel 4

FROM runtime AS speech
USER root
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libstdc++6 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=whisper-build /src/build/bin/whisper-cli /usr/local/bin/whisper-cli
USER tkc

FROM runtime AS default
