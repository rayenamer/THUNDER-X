"""Serve cklxx/laya-browser on /v1/systemone, inside Docker.

The repo ships its own server (laya_browser.py) but only on 127.0.0.1; this starts the same server on 0.0.0.0.
Downloads only what's needed (model + its laya_browser.py), at a pinned revision, into the /models volume.
"""

import os
import sys

from huggingface_hub import snapshot_download

REPO = "cklxx/laya-browser"
REVISION = os.environ.get("LAYA_BROWSER_REVISION", "645cf366a2ae35f1086e8c20eff48f909bb49206")

local = snapshot_download(
    REPO,
    revision=REVISION,
    allow_patterns=["model.safetensors", "rl_agent_config.json", "config.json", "laya_browser.py", "encoder/*", "tokenizer/*"],
)
sys.path.insert(0, local)
from laya_browser import LayaBrowser  # noqa: E402  (the repo's own wrapper: builds requests in its trained format)

print(f"loading {REPO}@{REVISION[:8]} from {local}", flush=True)
LayaBrowser.from_pretrained(local, device=os.environ.get("LAYA_DEVICE", "cpu")).serve(port=8000, host="0.0.0.0")
