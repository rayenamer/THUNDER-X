import { useState } from "react";
import StatusBadge from "./StatusBadge.jsx";

// The session's steps, in order, left to right (design §5.1).
export default function NodeChain({ nodes, selectedId, onSelect, onAdd }) {
  return (
    <section className="chain">
      {nodes.map((node, index) => (
        <div key={node.id} className="chain-item">
          <button
            className={`node-card status-${node.status} ${node.id === selectedId ? "selected" : ""}`}
            onClick={() => onSelect(node.id)}
          >
            <div className="node-top">
              <span className="node-number">{index + 1}</span>
              <StatusBadge status={node.status} />
            </div>
            <div className="node-prompt">{node.prompt}</div>
            {node.result?.xpath && (
              <code className="node-xpath" title={node.result.xpath}>
                {node.result.xpath}
              </code>
            )}
            {node.result && (
              <div className="muted small">
                {node.result.action} · {node.result.route ?? "-"} · {node.result.confidence.toFixed(2)}
              </div>
            )}
          </button>
          <span className="arrow">→</span>
        </div>
      ))}
      <AddNode onAdd={onAdd} />
    </section>
  );
}

function AddNode({ onAdd }) {
  const [prompt, setPrompt] = useState("");

  function submit(event) {
    event.preventDefault();
    if (!prompt.trim()) return;
    onAdd(prompt.trim());
    setPrompt("");
  }

  return (
    <form className="node-card add-card" onSubmit={submit}>
      <input
        className="input"
        placeholder="Add a step: click on About us"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
      />
      <button className="button primary" disabled={!prompt.trim()}>
        Add
      </button>
    </form>
  );
}
