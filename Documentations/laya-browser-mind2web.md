# laya-browser-mind2web

> Everything about Laya and the fine-tune comes from their public model cards and docs (sources at the end). Numbers are **their** measurements, not ours yet.

---

---

## 1. Laya

**Repo:** [convaiinnovations/laya](https://huggingface.co/convaiinnovations/laya) · Apache-2.0 · pip package `laya`

Laya is a "System 1" decision model: an encoder with **typed decision heads**. You give it a text (`state`) and a few typed questions; it answers all of them in one forward pass, with probabilities. It never generates text.


---

## 2. The fine-tune we use: Quantum08/laya-browser-mind2web

**Repo:** [Quantum08/laya-browser-mind2web](https://huggingface.co/Quantum08/laya-browser-mind2web) · Apache-2.0

| | |
|---|---|
| Base | `convaiinnovations/laya`, English root (ModernBERT-large, 421M) |
| Trained on | **Mind2Web only**: 8,613 decisions from 949 tasks on 69 websites |
| Training length | `max_len=768`, `head_max_len=448` |
| Files | `model.safetensors` (843 MB), `rl_agent_config.json`, `encoder/`, `tokenizer/` (the Laya layout, so `laya-serve` can load it) |
| Download | ~846 MB |

### What is Mind2Web?

A public dataset from Ohio State: over 2,000 tasks done by people on 137 real websites. Each step records the goal, the page, the element the person used and the operation (click, type, select). It's the standard benchmark for "pick the right element".

### Why this fine-tune

| | Quantum08 | ShaunSpark | cklxx | abedinia |
|---|---|---|---|---|
| Trained on | **Mind2Web only** | Mind2Web, 671 examples | Mind2Web + WebChain + NNetNav | Mind2Web + synthetic |
| Servable by `laya-serve` | **yes** | no (bare `.bin`) | its own server (`laya_browser.py serve`) | yes |
| Element accuracy, Mind2Web test | **0.48–0.50** | not comparable | not comparable | 0.27–0.35 |
| Published calibration | **yes** | no | no | no |

### Its reported scores (Mind2Web test, 20-candidate shortlist)

| Evaluation Split | Description | Element Accuracy | Operation Accuracy | Step Success |
|---|---|---:|---:|---:|
| **Cross-task** | Unseen tasks, potentially familiar websites. | 0.503 | 0.520 | 0.390 |
| **Cross-website** | Unseen websites, potentially familiar domains. | 0.482 | 0.478 | 0.329 |
| **Cross-domain** | Unseen website domains or categories. | 0.484 | 0.498 | 0.354 |


```

| Element Accuracy   | Did the model identify the correct HTML element?                                |
|*Operation Accuracy*| Did the model predict the correct action?                                       |
| Step Success       | Did the model correctly predict the complete interaction (element + operation)? |

```



**Read it as: about 1 right element out of 2.** On our own pages it could be better or worse. We'll know from our dev set .

### Hardware

| | CPU | GPU (T4) |
|---|---|---|
| Speed (base Laya, one question) | ~0.2–0.5 s | ~33 ms |
| Memory | not stated; plan ~2–3 GB RAM for a 421M model | |

For GPU: install the NVIDIA Container Toolkit, use a CUDA torch build in the Dockerfile, uncomment the `deploy:` block, set `LAYA_DEVICE: cuda`.

---

## 3. Talking to it

### Health

```bash
curl -s localhost:8001/health
```

### A request

```bash
curl -s localhost:8001/v1/systemone -H 'content-type: application/json' -d '{
  "model": "english",
  "state": "Instruction: hover over ok under Employee section",
  "questions": {
    "target": {
      "type": "choice",
      "instructions": "Which element does the instruction point at?",
      "criteria": {
        "e12": "<span> ok · section: Employee",
        "e40": "<button> OK · section: Manager",
        "none": "none of these elements"
      }
    }
  }
}'
```

> This shape is the generic Laya API. For real accuracy, `state` and `questions` must follow the jev_ultrafast format the fine-tune was trained on (§4).

### The answer

```json
{
  "answers": {
    "target": {
      "type": "choice",
      "choice": "e12",
      "probabilities": {"e12": 0.91, "e40": 0.08, "none": 0.01},
      "answer_confidence": 0.91,
      "confidence": 0.78,
      "x_jev_confidence": 0.86
    }
  },
  "usage": {"input_tokens": 83, "truncated": false},
  "routing": {"model": "english"}
}
```


## 4. Known limits

- **English only.** The fine-tune is built on the English root. French instructions will likely score lower. 
- **~50% element accuracy** 
- **Format-sensitive.** I needed to re formulate the format.
- **Short lists.** Accuracy drops as options grow (base Laya: 0.95 with 4 labels, 0.425 with 77). Keep the shortlist at 20 or fewer.


---

## 5. The other choice: cklxx/laya-browser

Since the benchmark (precision 74% vs 68%), [cklxx/laya-browser](https://huggingface.co/cklxx/laya-browser) is the **default**; `LAYA_MODEL=mind2web ./run.sh …` switches back to Quantum08 (Docker service `laya-browser`, :8002, pinned to revision `645cf36`).

| | Quantum08 | cklxx (default) |
|---|---|---|
| Base | ModernBERT-large, 421M | mmBERT-base (multilingual), 322M |
| Trained on | Mind2Web only | WebChain real-site trajectories + webgym forms + DAgger |
| Published scores | Mind2Web test splits (element acc 0.48–0.50) | its own suites only: not comparable |
| Request format | jev_ultrafast (`helpers.build_mind2web_request`) | its "v5" format (`helpers.build_browser_request`) |
| Shortlist | 20 | 60 (trained on up to 60 options) |

Which one is better for Thunder-X: run `labs/kpi_lab.ipynb` once with each, and compare the `laya` route.

