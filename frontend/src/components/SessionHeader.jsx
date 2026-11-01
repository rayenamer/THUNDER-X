const MODES = [
  { id: "validate", label: "Validate", hint: "Check each XPath, touch nothing" },
  { id: "act", label: "Act", hint: "Also do each action: the next step runs on the page it leaves" },
];

export default function SessionHeader({ session, busy, onMode, onRunAll, onClose, onReopen }) {
  return (
    <header className="session-header">
      <div>
        <h1>{session.title || "Session"}</h1>
        <div className="muted small mono">{session.url}</div>
      </div>

      {session.closed ? (
        <div className="actions">
          <span className="badge badge-waiting">Closed · {formatDate(session.openedAt)}</span>
          <button className="button primary" onClick={onReopen} disabled={busy} title="A new window on the same page, with these steps">
            {busy ? "Opening…" : "Reopen"}
          </button>
        </div>
      ) : (
        <div className="actions">
          <div className="segmented" role="radiogroup" aria-label="Mode">
            {MODES.map((mode) => (
              <button
                key={mode.id}
                role="radio"
                aria-checked={session.mode === mode.id}
                className={session.mode === mode.id ? "active" : ""}
                title={mode.hint}
                disabled={busy}
                onClick={() => onMode(mode.id)}
              >
                {mode.label}
              </button>
            ))}
          </div>
          <button className="button" onClick={onClose} disabled={busy}>
            Close
          </button>
          <button className="button primary" onClick={onRunAll} disabled={busy || !session.nodes?.length}>
            {busy ? "Running…" : "Run all"}
          </button>
        </div>
      )}
    </header>
  );
}

export function formatDate(isoDate) {
  if (!isoDate) return "";
  return new Date(isoDate).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}
