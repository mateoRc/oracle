FROM python:3.13-slim AS base

ARG VERSION=dev
LABEL org.opencontainers.image.title="Oracle" \
      org.opencontainers.image.version="${VERSION}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ORACLE_VERSION="${VERSION}"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --requirement requirements.txt

FROM base AS test

COPY requirements-dev.txt .
RUN pip install --no-cache-dir --requirement requirements-dev.txt

COPY app app
COPY tests tests
RUN python -m pytest

FROM base AS runtime

RUN useradd --create-home oracle
COPY --from=test --chown=oracle:oracle /app/app app

USER oracle
EXPOSE 8080

HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=10 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
