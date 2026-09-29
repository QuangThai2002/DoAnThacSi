FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Các thư viện embedding/Chroma cần một số công cụ hệ thống khi cài trên Linux.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY src ./src
COPY data ./data
COPY .streamlit ./.streamlit
COPY docs/deployment.md ./docs/deployment.md

# Không chạy Streamlit bằng root trong container.
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/data/local_store \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl --fail http://127.0.0.1:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "src/shopee_seller_ai.py", "--server.address=0.0.0.0", "--server.port=8501"]
