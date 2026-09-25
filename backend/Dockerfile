# backend/Dockerfile
# FastAPI service. Built to match the versions verified in requirements.txt
# (see that file's header comment for the exact dev-venv snapshot date).

FROM python:3.11-slim AS base

# Keep Python from writing .pyc files / buffering stdout, and stop pip from
# nagging about a root install inside the image (there's no venv to isolate).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps needed to build any wheel-less packages (e.g. cryptography
# backends for pyjwt[crypto]); the slim base + this single stage keeps
# the image reasonably small without a separate builder stage.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

# Run as a non-root user
RUN useradd --create-home --uid 1000 appuser
COPY --chown=appuser:appuser . .
USER appuser

EXPOSE 8000

# Basic liveness check against the app's root health-check route
# (see app/main.py's health_check()).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
