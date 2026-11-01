import { useEffect, useState } from "react";
import * as api from "./api.js";
import Sidebar from "./components/Sidebar.jsx";
import OpenPage from "./components/OpenPage.jsx";
import SessionHeader from "./components/SessionHeader.jsx";
import NodeChain from "./components/NodeChain.jsx";
import NodeDetail from "./components/NodeDetail.jsx";
import Navigator from "./components/Navigator.jsx";

// A session = one browser window + a chain of nodes (design §5).
// A node = one instruction, its status and the executor's result.

const NODE_STATUS = { verified: "done", failed: "failed", not_found: "not_found" };

function newNode(prompt) {
  return { id: crypto.randomUUID(), prompt, status: "waiting", result: null };
}

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [apiOnline, setApiOnline] = useState(false);

  const session = sessions.find((s) => s.id === activeId);
  const selectedNode = session?.nodes.find((n) => n.id === selectedNodeId);
  const lastResult = session ? lastRunResult(session.nodes) : null;

  useEffect(() => {
    const check = () => api.health().then(() => setApiOnline(true)).catch(() => setApiOnline(false));
    check();
    const timer = setInterval(check, 10000);
    return () => clearInterval(timer);
  }, []);

  function changeSession(sessionId, change) {
    setSessions((list) => list.map((s) => (s.id === sessionId ? change(s) : s)));
  }

  function changeNode(sessionId, nodeId, change) {
    changeSession(sessionId, (s) => ({
      ...s,
      nodes: s.nodes.map((n) => (n.id === nodeId ? { ...n, ...change } : n)),
    }));
  }

  async function openPage(url, showWindow) {
    setBusy(true);
    setError(null);
    try {
      const info = await api.openSession(url, showWindow);
      const created = { id: info.session_id, url: info.url, title: info.title, nodes: [] };
      setSessions((list) => [...list, created]);
      setActiveId(created.id);
      setSelectedNodeId(null);
    } catch (e) {
      setError(`Couldn't open the page. ${e.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function closeSession() {
    await api.closeSession(session.id).catch(() => {});
    setSessions((list) => list.filter((s) => s.id !== session.id));
    setActiveId(null);
  }

  function addNode(prompt) {
    const node = newNode(prompt);
    changeSession(session.id, (s) => ({ ...s, nodes: [...s.nodes, node] }));
    setSelectedNodeId(node.id);
  }

  // Editing a node makes it and every node after it stale: their page depended on it (design §5.3).
  function editNode(nodeId, prompt) {
    changeSession(session.id, (s) => {
      const index = s.nodes.findIndex((n) => n.id === nodeId);
      const nodes = s.nodes.map((n, i) => {
        if (i < index) return n;
        const edited = i === index ? { prompt } : {};
        return { ...n, ...edited, status: "waiting", result: null };
      });
      return { ...s, nodes };
    });
  }

  async function runNode(node) {
    const sessionId = session.id;
    changeNode(sessionId, node.id, { status: "running" });
    try {
      const result = await api.runStep(sessionId, node.prompt);
      const status = NODE_STATUS[result.status];
      changeNode(sessionId, node.id, { status, result });
      return status;
    } catch (e) {
      changeNode(sessionId, node.id, { status: "failed", result: null });
      setError(`Step failed to run. ${e.message}`);
      return "failed";
    }
  }

  // Every node in order, in the same window. Stops at the first one that isn't done.
  async function runAll() {
    setBusy(true);
    for (const node of session.nodes) {
      setSelectedNodeId(node.id);
      const status = await runNode(node);
      if (status !== "done") break;
    }
    setBusy(false);
  }

  return (
    <div className="app">
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        apiOnline={apiOnline}
        onSelect={(id) => { setActiveId(id); setSelectedNodeId(null); }}
        onNew={() => setActiveId(null)}
      />

      <main className="main">
        {error && (
          <div className="banner" onClick={() => setError(null)}>{error}</div>
        )}

        {!session && <OpenPage busy={busy} onOpen={openPage} />}

        {session && (
          <>
            <SessionHeader session={session} busy={busy} onRunAll={runAll} onClose={closeSession} />
            <NodeChain
              nodes={session.nodes}
              selectedId={selectedNodeId}
              onSelect={setSelectedNodeId}
              onAdd={addNode}
            />
            <div className="workspace">
              <NodeDetail
                key={selectedNode?.id ?? "none"} /* a new step slides in instead of swapping in place */
                node={selectedNode}
                index={session.nodes.indexOf(selectedNode)}
                busy={busy}
                onRun={runNode}
                onEdit={editNode}
              />
              {/* The box is only drawn for the last run: older steps' elements may have moved since */}
              <Navigator
                url={lastResult?.url ?? session.url}
                result={lastResult}
                showHighlight={!selectedNode || selectedNode.result === lastResult}
              />
            </div>
          </>
        )}
      </main>
    </div>
  );
}

// The latest node that has a result: what the browser window shows now.
function lastRunResult(nodes) {
  const withResult = nodes.filter((n) => n.result);
  return withResult.length ? withResult[withResult.length - 1].result : null;
}
