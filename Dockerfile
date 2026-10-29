FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY Model-20261025T155233Z-1-001/Model ./Model-20261025T155233Z-1-001/Model

# HF Spaces mendengarkan $PORT (default 7860). Nilai EXPOSE hanya informatif.
EXPOSE 7860

# HF Spaces menetapkan PORT (default 7860). Nilai fallback dipakai supaya
# container juga bisa dijalankan lokal tanpa menyetel PORT (tanpa fallback,
# uvicorn gagal start dengan "--port requires an argument").
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
