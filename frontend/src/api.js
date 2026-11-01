// Calls to the Thunder-X service (forwarded by Vite, see vite.config.js).

async function request(method, path, body) {
  const response = await fetch(`/api${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status}: ${detail}`);
  }
  return response.json();
}

export function health() {
  return request("GET", "/health");
}

// Opens a browser window on the URL, recorded in LogsDb. It stays open until closeSession.
// title: the session's name; empty -> the page's own title.
export function openSession(url, title) {
  return request("POST", "/sessions", { url, title: title || null });
}

export function closeSession(sessionId) {
  return request("DELETE", `/sessions/${sessionId}`);
}

export function navigate(sessionId, url) {
  return request("POST", `/page-extractor/sessions/${sessionId}/navigate`, { url });
}

// Runs the whole pipeline for one step, on the page as the session's window shows it now.
// position: the step's place in the chain (1, 2, 3...), so LogsDb files the run under the right prompt.
// mode "validate": check the XPath only. "act": also do the action.
export function runStep(sessionId, position, instruction, mode) {
  return request("POST", "/run", { session_id: sessionId, position, instruction, mode });
}

// Every recorded session, newest first.
export function listSessions() {
  return request("GET", "/logs/sessions");
}

// A session's whole history: prompts, their runs, each run's steps.
export function sessionHistory(sessionId) {
  return request("GET", `/logs/sessions/${sessionId}`);
}

// Where a recorded run's screenshot can be loaded from (an <img src>).
export function screenshotUrl(runId) {
  return `/api/logs/runs/${runId}/screenshot`;
}
