FROM python:3.12-slim-bookworm

# ── System deps (ffmpeg + ffprobe + build tools) ─────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# ── Python deps ──────────────────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── App source ───────────────────────────────────────────────────────────────
COPY *.py ./

# ── Output + temp dirs ───────────────────────────────────────────────────────
RUN mkdir -p /var/wellness/output /var/wellness/tmp

# ── Non-root user ────────────────────────────────────────────────────────────
RUN useradd -m -u 1000 wellness && \
    chown -R wellness:wellness /app /var/wellness
USER wellness

HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python3 -c "import mysql.connector; print('ok')" || exit 1

CMD ["python3", "pipeline.py"]
