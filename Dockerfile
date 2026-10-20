# ============================================================
# Ombre Brain Docker Build
# Docker 构建文件
#
# Build: docker build -t ombre-brain .
# Run:   docker run -e OMBRE_API_KEY=your-key -p 8000:8000 ombre-brain
# ============================================================

FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (leverage Docker cache)
# 先装依赖（利用 Docker 缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files / 复制项目文件
COPY *.py .
COPY dashboard.html .
COPY config.example.yaml ./config.yaml

# Persistent bucket data lives in /app/buckets — mount a volume there
# (docker-compose / Railway volume). No VOLUME directive: Railway rejects it.
# 持久化：把卷挂到 /app/buckets（Railway 不支持 Dockerfile 里的 VOLUME）

# Default to streamable-http for container (remote access)
# 容器场景默认用 streamable-http
ENV OMBRE_TRANSPORT=streamable-http
ENV OMBRE_BUCKETS_DIR=/app/buckets

EXPOSE 8000

CMD ["python", "server.py"]
