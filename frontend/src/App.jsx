import { useEffect, useState } from "react";
import * as api from "./api.js";
import { NODE_STATUS, newNode, nodesFromHistory, sessionFromRecord } from "./history.js";
import Sidebar from "./components/Sidebar.jsx";
import OpenPage from "./components/OpenPage.jsx";
import SessionHeader from "./components/SessionHeader.jsx";
import NodeChain from "./components/NodeChain.jsx";
import NodeDetail from "./components/NodeDetail.jsx";
import Navigator from "./components/Navigator.jsx";

// A session = one browser window + a chain of nodes (design §5), recorded in LogsDb.
// A node = one instruction, its status and its latest result (with its screenshot and steps).
// Mode: "validate" checks each XPath only; "act" also does the action, so each node
// runs on the page the previous one left behind.
// A closed session (its window is gone) can be looked at, or reopened in a new window.

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [apiOnline, setApiOnline] = useState(false);

  const session = sessions.find((s) => s.id === activeId);
  const nodes = session?.nodes ?? [];
  const selectedNode = nodes.find((n) => n.id === selectedNodeId);
  const shownResult = selectedNode?.result ?? session?.lastResult ?? null;

  useEffect(() => {
    const check = () => api.health().then(() => setApiOnline(true)).catch(() => setApiOnline(false));
    check();
    const timer = setInterval(check, 10000);
    return () => clearInterval(timer);
  }, []);

  // The sidebar: every recorded session, newest first.
  useEffect(() => {
    api
      .listSessions()
      .then((records) => setSessions(records.map(sessionFromRecord)))
      .catch((e) => setError(`Couldn't load the past sessions. ${e.message}`));
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

  // Opening a session from the sidebar loads its history the first time.
  async function selectSession(sessionId) {
    setActiveId(sessionId);
    setSelectedNodeId(null);
    const chosen = sessions.find((s) => s.id === sessionId);
    if (chosen.nodes !== null) return;

    try {
      const history = await api.sessionHistory(sessionId);
      changeSession(sessionId, (s) => ({ ...s, nodes: nodesFromHistory(history) }));
    } catch (e) {
      setError(`Couldn't load this session's history. ${e.message}`);
    }
  }

  // A new browser window on the URL. `title`: the session's name (empty: the page's title).
  // `steps`: prompts to start with (when reopening a session).
  async function openPage(url, title, steps = []) {
    setBusy(true);
    setError(null);
    try {
      const info = await api.openSession(url, title);
      const created = {
        id: info.session_id,
        url: info.url, // where Run all starts from
        title: info.title,
        openedAt: new Date().toISOString(),
        closed: false,
        mode: "act",
        nodes: steps.map(newNode),
        lastResult: null,
      };
      setSessions((list) => [created, ...list]);
      setActiveId(created.id);
      setSelectedNodeId(null);
    } catch (e) {
      setError(`Couldn't open the page. ${e.message}`);
    } finally {
      setBusy(false);
    }
  }

  // The window closes; the session stays in the sidebar with its history.
  async function closeSession() {
    await api.closeSession(session.id).catch(() => {});
    changeSession(session.id, (s) => ({ ...s, closed: true }));
  }

  // A closed session's steps, in a new window on the same first page, under the same title.
  function reopenSession() {
    openPage(session.url, session.title, nodes.map((n) => n.prompt));
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
      const edited = s.nodes.map((n, i) => {
        if (i < index) return n;
        const change = i === index ? { prompt } : {};
        return { ...n, ...change, status: "waiting", result: null };
      });
      return { ...s, nodes: edited };
    });
  }

  function setMode(mode) {
    changeSession(session.id, (s) => ({ ...s, mode }));
  }

  async function runNode(node) {
    const sessionId = session.id;
    const position = nodes.findIndex((n) => n.id === node.id) + 1;
    changeNode(sessionId, node.id, { status: "running" });
    try {
      const result = await api.runStep(sessionId, position, node.prompt, session.mode);
      const status = NODE_STATUS[result.status];
      changeNode(sessionId, node.id, { status, result });
      changeSession(sessionId, (s) => ({ ...s, lastResult: result }));
      return status;
    } catch (e) {
      changeNode(sessionId, node.id, { status: "failed", result: null });
      setError(`Step failed to run. ${e.message}`);
      return "failed";
    }
  }

  // Every node in order, in the same window. Stops at the first one that isn't done.
  // In act mode the steps change the page, so the run starts again from the session's first page.
  async function runAll() {
    setBusy(true);
    setError(null);
    try {
      if (session.mode === "act") {
        await api.navigate(session.id, session.url);
      }
      changeSession(session.id, (s) => ({
        ...s,
        nodes: s.nodes.map((n) => ({ ...n, status: "waiting", result: null })),
      }));
      for (const node of nodes) {
        setSelectedNodeId(node.id);
        const status = await runNode(node);
        if (status !== "done") break;
      }
    } catch (e) {
      setError(`Couldn't go back to the first page. ${e.message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app">
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        apiOnline={apiOnline}
        onSelect={selectSession}
        onNew={() => setActiveId(null)}
      />

      <main className="main">
        {error && (
          <div className="banner" onClick={() => setError(null)}>{error}</div>
        )}

        {!session && <OpenPage busy={busy} onOpen={(url, title) => openPage(url, title)} />}

        {session && (
          <>
            <SessionHeader
              session={session}
              busy={busy}
              onMode={setMode}
              onRunAll={runAll}
              onClose={closeSession}
              onReopen={reopenSession}
            />

            {session.nodes === null ? (
              <p className="muted">Loading the session's history…</p>
            ) : (
              <>
                <NodeChain
                  nodes={nodes}
                  selectedId={selectedNodeId}
                  onSelect={setSelectedNodeId}
                  onAdd={session.closed ? null : addNode}
                />
                <div className="workspace">
                  <NodeDetail
                    key={selectedNode?.id ?? "none"} /* a new step slides in instead of swapping in place */
                    node={selectedNode}
                    index={nodes.indexOf(selectedNode)}
                    busy={busy}
                    readOnly={session.closed}
                    onRun={runNode}
                    onEdit={editNode}
                  />
                  {/* The selected step's own screenshot, or the latest one */}
                  <Navigator url={shownResult?.url ?? session.url} result={shownResult} />
                </div>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
