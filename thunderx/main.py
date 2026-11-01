"""The Thunder-X microservice. Each pipeline box is a folder with its own router, mounted here.

The pipeline endpoints (/sessions, /run) go through thunderx/pipeline.py, so LogsDb records them.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from thunderx import pipeline
from thunderx.element_finder.api import router as element_finder_router
from thunderx.logs_db import services as logs_db
from thunderx.logs_db.api import router as logs_db_router
from thunderx.nl_parser.api import router as nl_parser_router
from thunderx.page_extractor import services as page_extractor
from thunderx.page_extractor.api import router as page_extractor_router
from thunderx.page_extractor.models import SessionInfo


@asynccontextmanager
async def lifespan(app: FastAPI):
    logs_db.init_db()                  # data/logs.db and its tables, if they don't exist yet
    logs_db.close_open_sessions()      # windows from the previous run of the service are gone
    yield
    await page_extractor.close_all()   # don't leave browser windows behind


app = FastAPI(title="Thunder-X", version="0.1.0", summary="Natural language -> tested XPath", lifespan=lifespan)
app.include_router(nl_parser_router)
app.include_router(page_extractor_router)
app.include_router(element_finder_router)
app.include_router(logs_db_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/sessions", response_model=SessionInfo, tags=["pipeline"])
async def open_session(request: pipeline.OpenRequest) -> SessionInfo:
    """Open a browser window on a URL, and record the session under its title."""
    return await pipeline.open_session(request.url, title=request.title, headless=request.headless)


@app.delete("/sessions/{session_id}", tags=["pipeline"])
async def close_session(session_id: str) -> dict:
    """Close the browser window. The session's history stays in LogsDb."""
    try:
        await pipeline.close_session(session_id)
    except page_extractor.SessionNotFound:
        raise HTTPException(404, f"no session {session_id}")
    return {"closed": session_id}


@app.post("/run", response_model=pipeline.RunResponse, tags=["pipeline"])
async def run(request: pipeline.RunRequest) -> pipeline.RunResponse:
    """The whole pipeline on the page open in a session -> {action, xpath, value, confidence, status, run_id}.

    mode "validate" checks the XPath only; "act" also does the action and checks it worked.
    The run is recorded in LogsDb under the session's prompt at `position`.
    """
    try:
        return await pipeline.run_in_session(request.session_id, request.position, request.instruction, request.mode)
    except page_extractor.SessionNotFound:
        raise HTTPException(404, f"no session {request.session_id}")
