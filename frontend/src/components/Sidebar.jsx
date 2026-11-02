import { formatDate } from "./SessionHeader.jsx";

// Every recorded session: the open ones (a live browser window), then the past ones.
export default function Sidebar({ sessions, activeId, apiOnline, onSelect, onHome, onNew }) {
  const open = sessions.filter((s) => !s.closed);
  const past = sessions.filter((s) => s.closed);

  return (
    <aside className="sidebar">
      <button className="logo" onClick={onHome} title="Home">
        thunder<span className="logo-x">x</span>
      </button>

      <button className="button primary full" onClick={onNew}>
        New session
      </button>

      <nav className="session-list">
        {sessions.length === 0 && <div className="muted small">No session yet</div>}
        <SessionGroup title="Open" sessions={open} activeId={activeId} onSelect={onSelect} />
        <SessionGroup title="Past" sessions={past} activeId={activeId} onSelect={onSelect} />
      </nav>

      <div className="sidebar-footer">
        <span className={`dot ${apiOnline ? "dot-done" : "dot-failed"}`} />
        {apiOnline ? "Service online" : "Service offline"}
      </div>
    </aside>
  );
}

function SessionGroup({ title, sessions, activeId, onSelect }) {
  if (sessions.length === 0) return null;
  return (
    <>
      <div className="sidebar-title">{title}</div>
      {sessions.map((session) => (
        <button
          key={session.id}
          className={`session-item ${session.id === activeId ? "active" : ""}`}
          onClick={() => onSelect(session.id)}
        >
          <span className="session-name">
            <span className={`dot ${session.closed ? "dot-waiting" : "dot-done"}`} />
            {session.title || hostOf(session.url)}
          </span>
          <span className="muted small">
            {hostOf(session.url)} · {formatDate(session.openedAt)}
          </span>
        </button>
      ))}
    </>
  );
}

function hostOf(url) {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}
