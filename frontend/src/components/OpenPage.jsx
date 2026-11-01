import { useState } from "react";

export default function OpenPage({ busy, onOpen }) {
  const [url, setUrl] = useState("");
  const [showWindow, setShowWindow] = useState(true);

  function submit(event) {
    event.preventDefault();
    if (url.trim()) onOpen(url.trim(), showWindow);
  }

  return (
    <div className="hero">
      <form className="card open-card" onSubmit={submit}>
        <h1>Open a page</h1>
        <p className="muted">
          A browser window opens on this page and stays open. Each step you add runs on the page the
          previous step left behind.
        </p>

        <input
          className="input"
          placeholder="https://app.example.com"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          autoFocus
        />

        <label className="checkbox">
          <input type="checkbox" checked={showWindow} onChange={(e) => setShowWindow(e.target.checked)} />
          Show the browser window
        </label>

        <button className="button primary" disabled={busy || !url.trim()}>
          {busy ? "Opening…" : "Open"}
        </button>
      </form>
    </div>
  );
}
