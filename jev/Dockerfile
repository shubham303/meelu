FROM python:3.12-slim

WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 HF_HOME=/app/.cache/models

RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.8.0 \
 && pip install "transformers>=4.44,<5" safetensors huggingface_hub sentencepiece protobuf fastapi "uvicorn[standard]"

COPY server.py ./

EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
