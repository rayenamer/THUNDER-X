import { useEffect, useState } from "react";

// The home page: what Thunder-X does, how well (the benchmark), and how it compares.
// Numbers: labs/kpi_lab.ipynb on data/bench (178 cases, 11 public practice pages).

// ── content ───────────────────────────────────────────────────────────────

const DEMOS = [
  {
    url: "the-internet.herokuapp.com/login",
    instruction: "Type 'tomsmith' into the Username field",
    action: "type",
    xpath: "//*[@id='username']",
    route: "rules",
    ms: 410,
  },
  {
    url: "the-internet.herokuapp.com/tables",
    instruction: "Click 'edit' in Frank's row",
    action: "click",
    xpath: "//tr[td[normalize-space()='Frank']]//a[normalize-space()='edit']",
    route: "rules",
    ms: 530,
  },
  {
    url: "app.example.com/team",
    instruction: "Hover over 'ok' under the Employee section",
    action: "hover",
    xpath: "//section[.//h2[normalize-space()='Employee']]//span[normalize-space()='ok']",
    route: "laya",
    ms: 1840,
  },
];

const KPIS = [
  { value: 74, unit: "%", label: "Precision", hint: "when it answers, it's right" },
  { value: 70, unit: "%", label: "Accuracy", hint: "right answers / all cases" },
  { value: 94, unit: "%", label: "Coverage", hint: "cases it gave an XPath for" },
  { value: 78, unit: "%", label: "Action accuracy", hint: "click, type, select… read right" },
];

const PIPELINE = [
  { name: "Parse", text: "action · target · where", icon: "text" },
  { name: "Read the page", text: "every element, its label and section", icon: "globe" },
  { name: "Match by rules", text: "most steps end here, in ms", icon: "zap" },
  { name: "laya-browser", text: "only when the rules can't decide", icon: "cpu", optional: true },
  { name: "Verify the XPath", text: "1 match, the right element", icon: "check" },
];

const WHY = [
  ["globe", "Only a URL and a sentence", "The others need a page already opened and driven by your code, an HTML dump, or a screenshot pipeline."],
  ["zap", "No LLM on easy steps", "Most steps are solved by rules in milliseconds. A small local model (laya-browser, 322M, CPU) steps in only when the rules can't decide."],
  ["check", "A tested XPath, not a guess", "It runs on the live page before it's returned: exactly one match, and it's the element that was picked."],
  ["shield", "Stable XPaths", "//*[@id='username'] survives a redesign. /html/body/div[2]/form/input[1] doesn't."],
  ["searchx", "\"Not found\" is an answer", "A wrong answer becomes a silent bad test. \"Not found\" comes back to you, and you fix it in seconds."],
  ["repeat", "Repeatable", "Same page + same sentence → same XPath. A test suite can't depend on sampling."],
  ["lock", "Private and free", "Nothing is sent to a cloud LLM. No cost per step."],
];

const TOOLS = ["Thunder-X", "Stagehand", "browser-use", "MindAct", "Vision models"];
const TOOL_NOTES = ["", "observe()", "get_element_by_prompt()", "Mind2Web", "UGround / ShowUI"];

// [row, [text, tone] per tool]   tone: good · bad · mid · plain
const COMPARISON = [
  ["Input", [["URL + sentence", "good"], ["a page you drive", "plain"], ["a session you open", "plain"], ["the page's HTML", "plain"], ["a screenshot", "plain"]]],
  ["LLM needed", [["no", "good"], ["yes", "bad"], ["yes", "bad"], ["no", "good"], ["2–3B vision model", "mid"]]],
  ["Cost per step", [["none", "good"], ["API or self-hosted", "bad"], ["API or self-hosted", "bad"], ["none", "good"], ["none", "good"]]],
  ["Hardware", [["CPU", "good"], ["the LLM's", "mid"], ["the LLM's", "mid"], ["CPU", "good"], ["GPU", "bad"]]],
  ["Output", [["XPath + action + value + confidence", "good"], ["XPath + action", "mid"], ["an element", "mid"], ["an element", "mid"], ["a pixel", "bad"]]],
  ["XPath style", [["stable first", "good"], ["positional", "bad"], ["–", "plain"], ["–", "plain"], ["–", "plain"]]],
  ["Tested on the page", [["yes", "good"], ["no", "bad"], ["–", "plain"], ["–", "plain"], ["–", "plain"]]],
  ["Can say \"not here\"", [["yes", "good"], ["partly", "mid"], ["partly", "mid"], ["no", "bad"], ["no", "bad"]]],
  ["Same answer every time", [["yes", "good"], ["no", "bad"], ["no", "bad"], ["yes", "good"], ["yes", "good"]]],
  ["Explains itself", [["every step logged", "good"], ["short description", "mid"], ["no", "bad"], ["no", "bad"], ["no", "bad"]]],
  ["Data leaves the machine", [["no", "good"], ["if cloud LLM", "bad"], ["if cloud LLM", "bad"], ["no", "good"], ["no", "good"]]],
];

// ── icons (stroke, 24×24) ─────────────────────────────────────────────────

const ICONS = {
  globe: <><circle cx="12" cy="12" r="10" /><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20" /></>,
  zap: <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z" />,
  check: <><circle cx="12" cy="12" r="10" /><path d="m8 12 3 3 5-6" /></>,
  shield: <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />,
  searchx: <><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3M8.5 8.5l5 5M13.5 8.5l-5 5" /></>,
  repeat: <><path d="m17 2 4 4-4 4" /><path d="M3 11v-1a4 4 0 0 1 4-4h14" /><path d="m7 22-4-4 4-4" /><path d="M21 13v1a4 4 0 0 1-4 4H3" /></>,
  lock: <><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></>,
  cpu: <><rect x="4" y="4" width="16" height="16" rx="2" /><rect x="9" y="9" width="6" height="6" /><path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3" /></>,
  text: <path d="M4 7V4h16v3M9 20h6M12 4v16" />,
  arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
};

function Icon({ name, size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {ICONS[name]}
    </svg>
  );
}

// ── page ──────────────────────────────────────────────────────────────────

export default function Home({ onStart }) {
  return (
    <div className="home">
      <Hero onStart={onStart} />
      <Pipeline />
      <Benchmark />
      <Why />
      <Comparison />
      <LlmNote onStart={onStart} />
    </div>
  );
}

function Hero({ onStart }) {
  return (
    <section className="hx-hero">
      <div className="hx-glow hx-glow-a" />
      <div className="hx-glow hx-glow-b" />

      <div className="hx-hero-text">
        <span className="hx-badge"><Icon name="zap" size={14} /> No LLM · runs on CPU · tested on the live page</span>
        <h1 className="hx-headline">
          Natural language
          <br />
          <span className="hx-gradient">→ actionable XPath</span>
        </h1>
        <p className="hx-lead">
          Give Thunder-X a URL and a sentence. It opens the page, finds the element, and returns an XPath it
          has already run: one match, the right element.
        </p>
        <div className="hx-actions">
          <button className="hx-button hx-button-primary" onClick={onStart}>
            Start a session <Icon name="arrow" size={16} />
          </button>
          <a className="hx-button hx-button-ghost" href="#benchmark">See the benchmark</a>
        </div>
      </div>

      <Demo />
    </section>
  );
}

function Demo() {
  const [index, setIndex] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => setIndex((i) => (i + 1) % DEMOS.length), 4200);
    return () => clearInterval(timer);
  }, []);
  const demo = DEMOS[index];

  return (
    <div className="hx-demo">
      <div className="hx-demo-bar">
        <span className="hx-dot" /><span className="hx-dot" /><span className="hx-dot" />
        <span className="hx-demo-title">POST /run</span>
      </div>
      <div className="hx-demo-body" key={index}>
        <div className="hx-demo-line"><span className="hx-key">url</span><span className="hx-str">{demo.url}</span></div>
        <div className="hx-demo-line"><span className="hx-key">instruction</span><span className="hx-str">"{demo.instruction}"</span></div>
        <div className="hx-demo-arrow"><Icon name="arrow" size={16} /></div>
        <div className="hx-demo-line"><span className="hx-key">action</span><span className="hx-val">{demo.action}</span></div>
        <div className="hx-demo-line"><span className="hx-key">xpath</span><span className="hx-xpath">{demo.xpath}</span></div>
        <div className="hx-demo-meta">
          <span className="hx-pill hx-pill-good"><Icon name="check" size={13} /> verified · 1 match</span>
          <span className={`hx-pill ${demo.route === "laya" ? "hx-pill-violet" : "hx-pill-blue"}`}>route · {demo.route}</span>
          <span className="hx-pill hx-pill-dim">{(demo.ms / 1000).toFixed(2)} s</span>
        </div>
      </div>
      <div className="hx-demo-steps">
        {DEMOS.map((_, i) => (
          <button key={i} className={`hx-step-dot ${i === index ? "on" : ""}`} onClick={() => setIndex(i)}
                  aria-label={`example ${i + 1}`} />
        ))}
        <span className="hx-demo-note">examples</span>
      </div>
    </div>
  );
}

function Pipeline() {
  return (
    <section className="hx-section">
      <SectionTitle kicker="How it works" title="Rules first. A small model only when they can't decide." />
      <div className="hx-pipeline">
        {PIPELINE.map((step, i) => (
          <div className="hx-pipe-item" key={step.name}>
            <div className={`hx-pipe-card ${step.optional ? "optional" : ""}`}>
              <div className="hx-pipe-icon"><Icon name={step.icon} /></div>
              <div className="hx-pipe-name">{step.name}</div>
              <div className="hx-pipe-text">{step.text}</div>
              {step.optional && <span className="hx-pipe-tag">only if needed</span>}
            </div>
            {i < PIPELINE.length - 1 && <div className="hx-pipe-arrow"><Icon name="arrow" size={18} /></div>}
          </div>
        ))}
      </div>
    </section>
  );
}

function Benchmark() {
  return (
    <section className="hx-section" id="benchmark">
      <SectionTitle kicker="Benchmark" title="178 cases on 11 public pages, checked by execution" />
      <div className="hx-kpis">
        {KPIS.map((kpi) => (
          <div className="hx-kpi" key={kpi.label}>
            <div className="hx-kpi-value">{kpi.value}<span>{kpi.unit}</span></div>
            <div className="hx-kpi-label">{kpi.label}</div>
            <div className="hx-bar"><div className="hx-bar-fill" style={{ width: `${kpi.value}%` }} /></div>
            <div className="hx-kpi-hint">{kpi.hint}</div>
          </div>
        ))}
        <div className="hx-kpi hx-kpi-time">
          <div className="hx-kpi-value">0.69<span>s</span></div>
          <div className="hx-kpi-label">Median time per step</div>
          <div className="hx-kpi-hint">average 2.08 s · slowest 7.87 s</div>
          <div className="hx-kpi-hint">CPU only, no API call</div>
        </div>
      </div>
    </section>
  );
}

function Why() {
  return (
    <section className="hx-section">
      <SectionTitle kicker="Why it matters" title="Built for test automation, not for chat" />
      <div className="hx-why">
        {WHY.map(([icon, title, text]) => (
          <div className="hx-why-card" key={title}>
            <div className="hx-why-icon"><Icon name={icon} /></div>
            <div className="hx-why-title">{title}</div>
            <div className="hx-why-text">{text}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Comparison() {
  return (
    <section className="hx-section">
      <SectionTitle kicker="Compared" title="Thunder-X vs available tools" />
      <div className="hx-table-wrap">
        <table className="hx-table">
          <thead>
            <tr>
              <th />
              {TOOLS.map((tool, i) => (
                <th key={tool} className={i === 0 ? "ours" : ""}>
                  {tool}
                  {TOOL_NOTES[i] && <span className="hx-tool-note">{TOOL_NOTES[i]}</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {COMPARISON.map(([row, cells]) => (
              <tr key={row}>
                <th>{row}</th>
                {cells.map(([text, tone], i) => (
                  <td key={i} className={i === 0 ? "ours" : ""}>
                    <span className={`hx-cell hx-cell-${tone}`}>
                      {tone === "good" && "✓ "}{tone === "bad" && "✗ "}{tone === "mid" && "~ "}{text}
                    </span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function LlmNote({ onStart }) {
  return (
    <section className="hx-quote">
      <div className="hx-glow hx-glow-c" />
      <div className="hx-quote-kicker">What about large LLMs?</div>
      <p className="hx-quote-text">
        An LLM can't open a URL, whatever its size: it only reads the text it's given. To do this job it needs a
        system around it that opens the page, renders it, cleans the HTML, fits it in its context, and checks its
        answer.
      </p>
      <p className="hx-quote-punch">Thunder-X is that system, without the LLM.</p>
      <button className="hx-button hx-button-primary" onClick={onStart}>
        Try it on your page <Icon name="arrow" size={16} />
      </button>
    </section>
  );
}

function SectionTitle({ kicker, title }) {
  return (
    <div className="hx-section-title">
      <span className="hx-kicker">{kicker}</span>
      <h2>{title}</h2>
    </div>
  );
}
