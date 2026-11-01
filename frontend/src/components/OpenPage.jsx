import { useState } from "react";

export default function OpenPage({ busy, onOpen }) {
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");

  function submit(event) {
    event.preventDefault();
    if (url.trim()) onOpen(url.trim(), title.trim());
  }

  return (
    <div className="hero">
      <form className="card open-card" onSubmit={submit}>
        <h1>New session</h1>
        <p className="muted">
          A browser opens on this page and stays open. Each step you add runs on the page the
          previous step left behind.
        </p>

        <label className="field">
          <span className="field-label">Title</span>
          <input
            className="input"
            placeholder="Approve an employee (optional: the page's title otherwise)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            autoFocus
          />
        </label>

        <label className="field">
          <span className="field-label">Page</span>
          <input
            className="input"
            placeholder="https://app.example.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </label>

        <button className="button primary" disabled={busy || !url.trim()}>
          {busy ? "Opening…" : "Open"}
        </button>
      </form>
    </div>
  );
}
