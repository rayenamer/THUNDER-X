export default function SessionHeader({ session, busy, onRunAll, onClose }) {
  return (
    <header className="session-header">
      <div>
        <h1>{session.title || "Session"}</h1>
        <div className="muted small mono">{session.url}</div>
      </div>
      <div className="actions">
        <button className="button" onClick={onClose} disabled={busy}>
          Close
        </button>
        <button className="button primary" onClick={onRunAll} disabled={busy || session.nodes.length === 0}>
          {busy ? "Running…" : "Run all"}
        </button>
      </div>
    </header>
  );
}
