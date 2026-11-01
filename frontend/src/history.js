// LogsDb's records -> what the UI shows: sessions, nodes and results.
import { screenshotUrl } from "./api.js";

// The executor's status -> the node's status (StatusBadge, card colour).
export const NODE_STATUS = { verified: "done", no_change: "unsure", failed: "failed", not_found: "not_found" };

export function newNode(prompt) {
  return { id: crypto.randomUUID(), prompt, status: "waiting", result: null };
}

// A row of GET /logs/sessions -> a session in the sidebar. Its nodes load when it's opened.
export function sessionFromRecord(record) {
  return {
    id: record.id,
    url: record.start_url,
    title: record.title,
    openedAt: record.opened_at,
    closed: record.closed_at !== null,
    mode: "act",
    nodes: null, // not loaded yet
    lastResult: null,
  };
}

// GET /logs/sessions/{id} -> the session's nodes: one per prompt, showing its latest run.
export function nodesFromHistory(history) {
  return history.prompts.map(({ prompt, runs }) => {
    const latest = runs[0]; // newest first
    const result = latest ? resultFromRun(latest) : null;
    return {
      id: `prompt-${prompt.id}`,
      prompt: prompt.instruction,
      status: result ? NODE_STATUS[result.status] : "waiting",
      result,
    };
  });
}

// A recorded run -> the same shape as POST /run's answer, so every component reads both the same way.
function resultFromRun({ run, steps, has_screenshot, highlight }) {
  return {
    run_id: run.id,
    action: run.action,
    xpath: run.xpath,
    value: run.value,
    confidence: run.confidence,
    route: run.route,
    status: run.status,
    effect: run.effect,
    reason: run.reason,
    steps: steps.map((step) => `${step.part}: ${step.message}`),
    url: run.page_url_after ?? run.page_url,
    screenshot: null,
    screenshotSrc: has_screenshot ? screenshotUrl(run.id) : null,
    highlight,
  };
}

// The image of a result: the recorded one (a URL), or the fresh one from POST /run (base64).
export function imageOf(result) {
  if (result?.screenshotSrc) return result.screenshotSrc;
  if (result?.screenshot) return `data:image/jpeg;base64,${result.screenshot}`;
  return null;
}
