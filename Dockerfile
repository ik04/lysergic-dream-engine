FROM python:3.11-slim

# -------------------------
# System deps
# -------------------------
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    libsndfile1 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# -------------------------
# Workdir
# -------------------------
WORKDIR /app

# -------------------------
# Python deps
# -------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -------------------------
# Copy project files
# -------------------------
COPY . .

# -------------------------
# Runtime dirs
# -------------------------
RUN mkdir -p temp output

# -------------------------
# Env defaults (override via .env)
# -------------------------
ENV PYTHONUNBUFFERED=1 \
    TTS_CACHE_DIR=/app/.tts_cache

# -------------------------
# Entrypoint
# -------------------------
ENTRYPOINT ["python", "main.py"]
