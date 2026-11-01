import StatusBadge from "./StatusBadge.jsx";

// One step, opened: its XPath, how it was found, and every part's step (design §5.2).
// readOnly: a closed session's step, to look at only.
export default function NodeDetail({ node, index, busy, readOnly, onRun, onEdit }) {
  if (!node) {
    return (
      <section className="card detail empty">
        <p className="muted">{readOnly ? "Select a step in the chain." : "Add a step, or select one in the chain."}</p>
      </section>
    );
  }

  const result = node.result;

  return (
    <section className="card detail">
      <div className="detail-header">
        <h2>Step {index + 1}</h2>
        <StatusBadge status={node.status} />
      </div>

      <input
        className="input"
        value={node.prompt}
        readOnly={readOnly}
        onChange={(e) => onEdit(node.id, e.target.value)}
      />

      <dl className="facts">
        <dt>XPath</dt>
        <dd className="mono">{result?.xpath ?? "—"}</dd>

        <dt>Action</dt>
        <dd>{result?.action ?? "—"}{result?.value ? ` · "${result.value}"` : ""}</dd>

        <dt>Route</dt>
        <dd>{result ? `${result.route ?? "—"} · confidence ${result.confidence.toFixed(2)}` : "—"}</dd>

        <dt>Status</dt>
        <dd>{result ? <StatusBadge status={node.status} /> : "—"}</dd>

        {result?.effect && (
          <>
            <dt>Effect</dt>
            <dd>{result.effect}</dd>
          </>
        )}

        {result?.reason && (
          <>
            <dt>Reason</dt>
            <dd>{result.reason}</dd>
          </>
        )}
      </dl>

      {!readOnly && (
        <button className="button primary" onClick={() => onRun(node)} disabled={busy || node.status === "running"}>
          {node.status === "running" ? "Running…" : "Run this step"}
        </button>
      )}

      <h3>Timeline</h3>
      <Timeline steps={result?.steps ?? []} />
    </section>
  );
}

// "laya: picked Inspirations (link)" -> part "laya", text "picked Inspirations (link)"
function Timeline({ steps }) {
  if (steps.length === 0) {
    return <p className="muted small">Run the step to see what each part did.</p>;
  }
  return (
    <ol className="timeline">
      {steps.map((step, i) => {
        const [part, ...rest] = step.split(":");
        return (
          <li key={i} style={{ animationDelay: `${i * 50}ms` }}>
            <span className="timeline-part">{part}</span>
            <span>{withColoredMarks(rest.join(":").trim())}</span>
          </li>
        );
      })}
    </ol>
  );
}

// "text ✘ 3 matches" -> the ✘ in red, the ✔ in green
function withColoredMarks(text) {
  return text.split(/([✔✘])/).map((piece, i) => {
    if (piece === "✔") return <span key={i} className="ok">✔</span>;
    if (piece === "✘") return <span key={i} className="fail">✘</span>;
    return piece;
  });
}
