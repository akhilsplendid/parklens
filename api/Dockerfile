FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .
COPY parklens ./parklens
# The knowledge base is generated locally (scripts/extract_kb.py) and copied into the image
# at build time; it is not committed to git. Build from the repo root context:
#   docker build -f api/Dockerfile -t parklens-api .
COPY data/generated/kb.json /app/kb.json
ENV KB_PATH=/app/kb.json
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "parklens.main:app", "--host", "0.0.0.0", "--port", "8000"]
