# cklxx/laya-browser (Laya fine-tuned on real-site browsing) behind its own /v1/systemone server.
# The other choice is docker/laya (Quantum08/laya-browser-mind2web). Pick with LAYA_MODEL (see run.sh).
FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    USE_TF=0 \
    HF_HOME=/models

# CPU-only PyTorch first, so pip doesn't pull the multi-GB CUDA build.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install laya huggingface_hub

COPY serve.py /app/serve.py

# The model is downloaded on first start into /models (a volume).
VOLUME /models
EXPOSE 8000

CMD ["python", "/app/serve.py"]
