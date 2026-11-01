# Laya (convaiinnovations/laya) behind its own HTTP server, laya-serve.
# No official image is published, so we build one from the pip package.
FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    USE_TF=0 \
    HF_HOME=/models

# CPU-only PyTorch first, so pip doesn't pull the multi-GB CUDA build.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install "laya[serve]"

# The model weights are downloaded on first start into /models (a volume).
# Which model: see LAYA_EXTRA_MODELS in docker-compose.yml.
VOLUME /models
EXPOSE 8000

CMD ["laya-serve"]
