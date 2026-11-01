import { useEffect, useRef, useState } from "react";
import StatusBadge from "./StatusBadge.jsx";

const SLOT_WIDTH = 260; // one card (220px) + the arrow after it (40px)
const ARROW_WIDTH = 40;

// The session's steps, in order (design §5.1), laid out like a snake so it never scrolls sideways:
//
//   1 → 2 → 3 → 4
//                ↓
//   8 ← 7 ← 6 ← 5
//   ↓
//   9 → +
// onAdd: null for a closed session (no new steps).
export default function NodeChain({ nodes, selectedId, onSelect, onAdd }) {
  const [chainRef, perRow] = useSlotsPerRow();

  // Every slot of the chain: the steps, then the "Add a step" card at the end.
  const slots = nodes.map((node, index) => ({ node, index }));
  if (onAdd) slots.push({ add: true });
  const rows = splitIntoRows(slots, perRow);

  // All rows share the width of a full row, so a right-to-left row starts under the end of the one above.
  const rowWidth = Math.max(1, Math.min(perRow, slots.length)) * SLOT_WIDTH - ARROW_WIDTH;

  return (
    <section className="chain" ref={chainRef}>
      <div className="chain-rows" style={{ width: rowWidth }}>
        {rows.map((row, rowIndex) => {
          const backwards = rowIndex % 2 === 1;
          const lastRow = rowIndex === rows.length - 1;
          return (
            <div key={rowIndex}>
              <div className={`chain-row ${backwards ? "backwards" : ""}`}>
                {row.map((slot, i) => (
                  <div key={slot.add ? "add" : slot.node.id} className="chain-item">
                    {slot.add ? (
                      <AddNode onAdd={onAdd} />
                    ) : (
                      <NodeCard
                        node={slot.node}
                        index={slot.index}
                        selected={slot.node.id === selectedId}
                        onSelect={onSelect}
                      />
                    )}
                    {i < row.length - 1 && <span className="arrow">{backwards ? "←" : "→"}</span>}
                  </div>
                ))}
              </div>
              {!lastRow && <div className={`chain-turn ${backwards ? "left" : "right"}`}>↓</div>}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function NodeCard({ node, index, selected, onSelect }) {
  return (
    <button
      className={`node-card status-${node.status} ${selected ? "selected" : ""}`}
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

// How many cards fit on one row, updated when the window is resized.
function useSlotsPerRow() {
  const ref = useRef(null);
  const [perRow, setPerRow] = useState(4);

  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => {
      setPerRow(Math.max(1, Math.floor(entry.contentRect.width / SLOT_WIDTH)));
    });
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return [ref, perRow];
}

function splitIntoRows(items, perRow) {
  const rows = [];
  for (let i = 0; i < items.length; i += perRow) {
    rows.push(items.slice(i, i + perRow));
  }
  return rows;
}
