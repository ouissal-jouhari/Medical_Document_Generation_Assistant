FROM python:3.12-slim AS base
# Bibliothèques système requises par OpenCV (Docling) et moteur OCR Tesseract (embarqué, hors ligne).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /srv
RUN useradd --system --uid 10001 --create-home xeleron
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --extra ocr
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
RUN mkdir -p /var/log/xeleron /srv/storage \
    && chown -R xeleron /var/log/xeleron /srv/storage
USER xeleron
ENV PATH="/srv/.venv/bin:$PATH" HOME=/home/xeleron
# Poids des modèles Docling embarqués dans l'image (ADR 0007) : préchargés au build,
# aucun accès réseau à l'exécution (compatible on-premise).
RUN python -m app.adapters.docling_warmup
ENV HF_HUB_OFFLINE=1
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
# Migrations avec le propriétaire (MIGRATION_DATABASE_URL), puis service avec le rôle applicatif.
CMD ["sh", "-c", "alembic upgrade head && unset MIGRATION_DATABASE_URL APP_DB_PASSWORD PURGE_DB_PASSWORD && exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
