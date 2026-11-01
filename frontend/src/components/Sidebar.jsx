export default function Sidebar({ sessions, activeId, apiOnline, onSelect, onNew }) {
  return (
    <aside className="sidebar">
      <div className="logo">
        thunder<span className="logo-x">x</span>
      </div>

      <button className="button primary full" onClick={onNew}>
        New session
      </button>

      <div className="sidebar-title">Sessions</div>
      <nav className="session-list">
        {sessions.length === 0 && <div className="muted small">No session yet</div>}
        {sessions.map((session) => (
          <button
            key={session.id}
            className={`session-item ${session.id === activeId ? "active" : ""}`}
            onClick={() => onSelect(session.id)}
          >
            <span className="session-name">{session.title || hostOf(session.url)}</span>
            <span className="muted small">{hostOf(session.url)} · {session.nodes.length} steps</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <span className={`dot ${apiOnline ? "dot-done" : "dot-failed"}`} />
        {apiOnline ? "Service online" : "Service offline"}
      </div>
    </aside>
  );
}

function hostOf(url) {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}
