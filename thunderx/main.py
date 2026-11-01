"""The Thunder-X microservice. Each pipeline box is a folder with its own router, mounted here."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from thunderx import pipeline
from thunderx.element_finder.api import router as element_finder_router
from thunderx.element_finder.models import FindResult
from thunderx.nl_parser.api import router as nl_parser_router
from thunderx.page_extractor import services as page_extractor
from thunderx.page_extractor.api import router as page_extractor_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await page_extractor.close_all()  


app = FastAPI(title="Thunder-X", version="0.1.0", summary="Natural language -> tested XPath", lifespan=lifespan)
app.include_router(nl_parser_router)
app.include_router(page_extractor_router)
app.include_router(element_finder_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/run", response_model=FindResult, tags=["pipeline"])
async def run(request: pipeline.RunRequest) -> FindResult:
    """The whole pipeline on the page open in a session: nl_parser + page_extractor -> element_finder -> laya."""
    try:
        return await pipeline.run_in_session(request.session_id, request.instruction)
    except page_extractor.SessionNotFound:
        raise HTTPException(404, f"no session {request.session_id}")
