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

// Opens a browser window on the URL. It stays open until closeSession.
export function openSession(url, showWindow) {
  return request("POST", "/page-extractor/sessions", { url, headless: !showWindow });
}

export function closeSession(sessionId) {
  return request("DELETE", `/page-extractor/sessions/${sessionId}`);
}

// Runs the whole pipeline for one step, on the page as the session's window shows it now.
export function runStep(sessionId, instruction) {
  return request("POST", "/run", { session_id: sessionId, instruction });
}
