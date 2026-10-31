"""The Thunder-X microservice. Each pipeline box is a folder with its own router, mounted here."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from thunderx.element_finder.api import router as element_finder_router
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
