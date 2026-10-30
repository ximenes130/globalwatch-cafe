FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /srv

COPY pyproject.toml ./
COPY app ./app
RUN pip install . && useradd --create-home --uid 10001 api

USER api
EXPOSE 8000

# O Render injeta PORT; localmente vale 8000.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
