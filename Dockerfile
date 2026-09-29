# NumPy 2.5.x requires Python 3.12+; keep the image aligned with the
# local development environment used by this project.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt ./requirements.txt
# Cài PyTorch bản CPU trước. Nếu để pip tự chọn, nó sẽ tải thêm các thư viện
# NVIDIA/CUDA rất lớn dù ứng dụng này không sử dụng GPU.
RUN pip install --upgrade pip \
    && pip install --index-url https://download.pytorch.org/whl/cpu "torch==2.13.0" \
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
    CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)" || exit 1

CMD ["streamlit", "run", "src/shopee_seller_ai.py", "--server.address=0.0.0.0", "--server.port=8501"]
