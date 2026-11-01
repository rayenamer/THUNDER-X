# Thunder-X: architecture v2

The system as built. Green = what a version adds. Dashed = planned, not built yet.

---

## 1. How it grew: one step, from naive to mature

### v0 · ask an AI

```mermaid
flowchart LR
    I[instruction] --> AI[LLM]:::new
    P[page HTML] --> AI
    AI --> X[XPath]
    classDef new fill:#d9f2d9,stroke:#2e7d32
```

**Problem:** it invents XPaths that match nothing. Slow, costly, and we can't tell if it's right.

### v1 · pick a real element, write the XPath with code

```mermaid
flowchart LR
    P[page] --> PE[page_extractor<br/>browser-use: the real elements]:::new
    I[instruction] --> AI[LLM picks one element]
    PE --> AI
    AI --> XB[xpath_builder<br/>XPath written from that element]:::new
    XB --> X[XPath]
    classDef new fill:#d9f2d9,stroke:#2e7d32
```

**Problem:** an LLM call for every step, even "click on About us".

### v2 · rules first

```mermaid
flowchart LR
    I[instruction] --> NL[nl_parser<br/>action · target · value]:::new
    P[page] --> PE[page_extractor]
    NL --> DM[direct matcher<br/>the element saying the target's text]:::new
    PE --> DM
    DM --> XB[xpath_builder] --> X[XPath]
    classDef new fill:#d9f2d9,stroke:#2e7d32
```

**Problem:** "hover over ok under Employee": two "ok" on the page.

### v3 · use the "where"

```mermaid
flowchart LR
    I[instruction] --> NL[nl_parser<br/>+ hint: under Employee]
    P[page] --> PE[page_extractor<br/>+ sections · boxes]
    NL --> CR[context resolver<br/>keep what fits the hint]:::new
    PE --> CR
    CR --> DM[direct matcher] --> XB[xpath_builder] --> X[XPath]
    classDef new fill:#d9f2d9,stroke:#2e7d32
```

**Problem:** synonyms, icons, vague wording: still 0 or 2+ matches.

### v4 · a small AI only when the rules can't decide

```mermaid
flowchart LR
    CR[context resolver] --> DM[direct matcher]
    DM -->|1 match| XB[xpath_builder]
    DM -->|0 or 2+| LA[laya<br/>Mind2Web fine-tune<br/>shortlist of 20]:::new
    LA -->|sure| XB
    LA -.->|not sure| LLM[LLM top 5]:::planned
    XB --> X[XPath]
    classDef new fill:#d9f2d9,stroke:#2e7d32
    classDef planned stroke-dasharray: 5 5
```

**Problem:** the XPath was never run: it may match 2 elements, the wrong one, or nothing.

### v5 · run it before trusting it

```mermaid
flowchart LR
    F[element_finder / laya] --> XB[xpath_builder<br/>stable styles first + alternatives]
    XB --> EX[executor · validate<br/>1 match AND same Chrome node]:::new
    EX -->|no| NEXT[next style]:::new
    NEXT --> EX
    EX -->|yes| X[verified XPath]
    classDef new fill:#d9f2d9,stroke:#2e7d32
```

**Problem:** nothing happens on the page: step 2 runs on the same page as step 1.

### v6 · do the action

```mermaid
flowchart LR
    XB[xpath_builder] --> V[validate]
    V --> A[act<br/>click · hover · type · select]:::new
    A --> W[wait until settled<br/>new page · new tab · SPA]:::new
    W --> C[check it changed]:::new
    C --> S[screenshot]:::new
    S --> X[verified XPath + effect]
    classDef new fill:#d9f2d9,stroke:#2e7d32
```

**Problem:** nobody sees what happened, and nothing is remembered.

### v7 · show it, record it

```mermaid
flowchart LR
    UI[UI<br/>chain of nodes · screenshots · timeline]:::new --> P[pipeline]
    P --> X[result]
    X --> UI
    X --> DB[(LogsDb<br/>session · prompt · run · steps · screenshot)]:::new
    classDef new fill:#d9f2d9,stroke:#2e7d32
```

**Problem:** the confidence isn't measured: 1.0 for the rules, Laya's own number for Laya.

### v8 · measure it

```mermaid
flowchart LR
    DB[(LogsDb + Mind2Web)] --> CI[CI score<br/>block a worse change]:::planned
    DB --> LAB[lab: % right per group]:::planned
    LAB --> T[(confidence table)]:::planned
    T --> P[pipeline: live confidence<br/>below τ → not found]:::planned
    classDef planned stroke-dasharray: 5 5,fill:#d9f2d9,stroke:#2e7d32
```

**Where we are:** v7 built, v8 designed (§13).

---

## 2. The whole picture

```mermaid
flowchart LR
    U[User] --> UI[UI · React<br/>sessions · nodes · screenshots]
    UI -->|/sessions · /run · /logs| API[Thunder-X service · FastAPI :8000]
    API --> P[pipeline.py<br/>the only place that knows the order]
    P --> CH[(Chrome<br/>browser-use · one per session)]
    P --> LY[Laya · Docker :8001<br/>Mind2Web fine-tune]
    P --> DB[(LogsDb · SQLite<br/>data/logs.db)]
    DB -. dataset .-> EV[Evaluation<br/>CI score · live confidence]:::planned
    EV -. confidence table .-> P
    classDef planned stroke-dasharray: 5 5
```

---

## 3. One step, end to end

```mermaid
flowchart LR
    I[instruction] --> NL[nl_parser]
    S[session's window] --> PE[page_extractor]
    NL -->|parsed| EF[element_finder]
    PE -->|elements| EF
    EF -->|found| GATE{found?}
    GATE -->|yes| XB[xpath_builder]
    GATE -->|ambiguous · not_found| LA[laya]
    LA --> XB
    XB -->|XPath + alternatives| EX[executor]
    EX --> R[result]
    R --> LOG[(LogsDb)]
    R --> UI[UI]
```

---

## 4. What travels between the parts

Each part adds one thing; nothing is invented on the way.

```mermaid
flowchart TB
    subgraph NLP[nl_parser]
        A1["action · value · target · hint"]
    end
    subgraph PEX[page_extractor]
        A2["elements: label · role · sections · box<br/>attributes · backend_node_id"]
    end
    subgraph EFI[element_finder / laya]
        A3["element (one of the page's) · confidence · route"]
    end
    subgraph XPB[xpath_builder]
        A4["xpath + alternatives (style order)"]
    end
    subgraph EXE[executor]
        A5["status · effect · screenshot · highlight"]
    end

    A1 -->|"parsed (action, value ride along)"| A3
    A2 --> A3
    A3 -->|element| A4
    A1 -.->|action · value| A4
    A4 -->|xpath| A5
    A3 -.->|"element.backend_node_id (identity check)"| A5
    A4 -.->|"action · value (what to do)"| A5
```

| Field in the final result | Comes from |
|---|---|
| `action`, `value` | nl_parser |
| `confidence`, `route` | direct matcher (1.0) or Laya |
| `xpath` | xpath_builder, **verified** by the executor |
| `status`, `effect`, `screenshot` | executor |

---

## 5. nl_parser: rules only

```mermaid
flowchart LR
    T["'Type john into the Email field under Login'"] --> N[normalize<br/>fold: lowercase, no accents<br/>keeps original spelling]
    N --> A[read_action<br/>type]
    A --> V[read_value<br/>john]
    V --> H[read_hint<br/>under → within / below<br/>by anchor role]
    H --> G[read_target<br/>Email · textbox]
```

---

## 6. page_extractor: the page as a list

```mermaid
flowchart LR
    W[session's Chrome window] -->|browser-use DomService| T[DOM + accessibility + layout tree]
    T --> C[collect_elements]
    C --> E["PageElement<br/>label = Chrome's accessible name<br/>sections = headings around it<br/>interactive · visible · box"]
```

---

## 7. element_finder: where, then what

```mermaid
flowchart TB
    IN[parsed + elements] --> CR{hint?}
    CR -->|no| ALL[all elements]
    CR -->|within| SEC[elements in that section]
    SEC -->|no such section| BEL[fallback: below the anchor]
    CR -->|near · above · below · left · right| GEO[elements placed around the anchor<br/>nearest first]
    ALL & SEC & BEL & GEO --> DM[direct matcher]
    DM --> M{"text match<br/>(role preferred, not required)"}
    M --> PV[prefer visible · prefer interactive<br/>ordinal → nth in page order]
    PV -->|1| F[found · confidence 1.0]
    PV -->|2+| AM[ambiguous · candidates = matches]
    PV -->|0| NF[not_found · candidates = interactive elements of the context]
```

---

## 8. laya: only when the rules can't decide

```mermaid
flowchart TB
    IN[element_finder result] --> Q{found?}
    Q -->|yes| PASS[pass through untouched]
    Q -->|no| C{candidates}
    C -->|0| SK[skip]
    C -->|1| ONE[ambiguous: nothing to compare]
    C -->|2+| SL[shortlist 20<br/>jev_ultrafast lexical ranker]
    SL --> FMT["options 'label (role, =value)'<br/>question click_target / type_text_target / select_target"]
    FMT --> L[(Laya :8001<br/>/v1/systemone)]
    L --> CF{answer_confidence ≥ τ}
    CF -->|yes| FOUND[found · route laya · runners-up kept]
    CF -->|no| AMB[ambiguous · top 5]
    AMB -.-> LLM[LLM top 5]:::planned
    L -.->|down · timeout| PASS2[input returned, step says why]
    classDef planned stroke-dasharray: 5 5
```

---

## 9. xpath_builder: write, don't run

```mermaid
flowchart LR
    E[picked element] --> S1[test id] --> S2[id<br/>not generated] --> S3[aria-label · name · placeholder] --> S4[text] --> S5[text in section] --> S6[linked label] --> S7[position<br/>last resort]
    S1 -.->|first one| X[xpath]
    S2 & S3 & S4 & S5 & S6 & S7 -.-> ALT[alternatives, in order]
```

SVG elements are named by `local-name()`.

---

## 10. executor: run it, then (act mode) do it

```mermaid
flowchart TB
    IN[xpath + alternatives · element · action · value] --> V["1. validate<br/>1 match AND same Chrome node id"]
    V -->|"none passes"| FAIL[failed]
    V -->|ok| MODE{mode}
    MODE -->|validate| SHOT
    MODE -->|act| ACT["2. act<br/>click · hover · type · select · check<br/>(browser-use element actions)"]
    ACT --> TAB{new tab?} -->|yes| SW[switch to it]
    TAB -->|no| WAIT
    SW --> WAIT["3. wait<br/>loaded + unchanged 0.5 s (max 10 s)"]
    WAIT --> CHK{"4. check<br/>control state · URL · page fingerprint"}
    CHK -->|changed| VER[verified + effect]
    CHK -->|nothing| NC[no_change]
    VER & NC & FAIL --> SHOT[5. screenshot + highlight]
```

---

## 11. A session in the UI

```mermaid
sequenceDiagram
    participant U as User
    participant UI
    participant API as service
    participant B as Chrome
    participant DB as LogsDb
    U->>UI: New session (title, URL)
    UI->>API: POST /sessions
    API->>B: open (headless)
    API->>DB: Session
    U->>UI: add steps · Run all (act)
    UI->>API: navigate back to start URL
    loop each node, stop at first not verified
        UI->>API: POST /run (position, instruction, mode)
        API->>B: extract · validate · act
        API->>DB: Prompt · Run · Steps · Screenshot
        API-->>UI: result + run_id
    end
    U->>UI: Close
    API->>DB: closed_at
```

---

## 12. LogsDb

```mermaid
erDiagram
    SESSION ||--o{ PROMPT : "chain"
    PROMPT ||--o{ RUN : "executions"
    RUN ||--o{ STEP : "timeline"
    RUN ||--o| SCREENSHOT : "page after"
    SESSION {
        string id
        string start_url
        string title
        datetime opened_at
        datetime closed_at
    }
    PROMPT {
        int position
        string instruction
    }
    RUN {
        string mode
        json parsed
        json element
        string status
        string xpath
        float confidence
        string route
        string effect
        int duration_ms
    }
    STEP {
        int position
        string part
        string message
        bool ok
    }
    SCREENSHOT {
        blob image
        json highlight
    }
```

---

## 13. Evaluation: two systems

```mermaid
flowchart LR
    M2W[(Mind2Web<br/>+ own cases)] --> RUN[run the pipeline]
    RUN --> RES[(results)]
    RES --> CI[1 · CI score]:::planned
    RES --> LAB[2 · live confidence]:::planned
    classDef planned stroke-dasharray: 5 5
```

### 13.1 CI: score the system

```mermaid
flowchart LR
    R[results] --> CMP[compare to ground truth]
    CMP --> K[KPIs<br/>accuracy · precision · coverage]
    K --> SC[overall score]
    SC --> G{better or equal<br/>than main?}
    G -->|yes| SHIP[merge]
    G -->|no| BLOCK[block]
```

### 13.2 Live confidence: the lab, then runtime

```mermaid
flowchart TB
    subgraph LAB[lab · offline]
        R[results + right/wrong] --> COR[correlation of each column with right/wrong]
        COR --> PICK["pick group-by columns<br/>few · no duplicates · strongly correlated · available live"]
        PICK --> GRP[% right per group<br/>train split → check on test split<br/>≥ 30 examples per group]
        GRP --> TBL[(confidence table)]
    end
    subgraph LIVE[runtime]
        NEW[new prompt's run] --> KEY[its group]
        KEY --> LOOK[look up the table]
        TBL --> LOOK
        LOOK --> CONF[confidence = that group's % right]
        CONF --> TAU{≥ τ?}
        TAU -->|yes| OK[answer]
        TAU -->|no| NF[NOT_FOUND / next route]
    end
```

---

## 14. Where things run

```mermaid
flowchart LR
    subgraph HOST[./run.sh all]
        V[Vite UI :5173] -->|/api proxy| S[FastAPI :8000]
        S --> C[(Chrome · headless)]
        S --> F[(data/logs.db)]
    end
    S --> D[Docker: Laya :8001<br/>volume laya-models]
```
