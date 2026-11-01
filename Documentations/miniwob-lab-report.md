# MiniWoB++ lab: what it is, what the lab did, what we found

Notebook: `labs/confidence_lab_withMiniWoB++.ipynb` · data: `data/MiniWoB++/`

---

## 1. MiniWoB++ in one minute

MiniWoB++ is a set of **130 tiny web pages**, made to train and test web agents. Each page is a **task**: a 160×210 px box with one instruction on top and some widgets under it.

```text
┌────────────────────────────┐
│ Click on the "ok" button.  │  ← the instruction (#query)
├────────────────────────────┤
│ ut sit vel                 │
│ [yes] [submit]             │  ← the widgets (#area), random each time
│ [no]  [Ok]                 │
│ elit iaculis: [______]     │
└────────────────────────────┘
```

Two things make it different from Mind2Web:

1. **The page is random.** Every time it loads, a JavaScript function `genProblem()` picks new words, new buttons, and a new instruction. A page file alone isn't a test case. It's a test case *generator*.
2. **The page grades itself.** When you click, the page's own code says right (+1) or wrong (−1). In `click-button.html`: the button whose text matches gets `endEpisode(1.0)`, the others get `endEpisode(-1.0)`.

Because the pages are random, someone had to **record people doing them** to get fixed examples. That recording is the second repo: **the demos**.

---
