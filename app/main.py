from fastapi import FastAPI, Query
from app.utils import Output, QdrantService, DocumentService, Input
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize QdrantService and connect
    qdrant_service = QdrantService()
    qdrant_service.connect()

    # Initialize DocumentService and create documents
    pdf_path = Path(__file__).parent.parent / "docs" / "laws.pdf"
    document_service = DocumentService(path_to_pdf=pdf_path)
    documents = document_service.create_documents()

    # Load documents into Qdrant
    qdrant_service.load(documents)

    # Store services in app state for later use
    app.state.qdrant_service = qdrant_service
    app.state.document_service = document_service
    app.state.ready_for_queries = True
    
    yield

app = FastAPI(lifespan=lifespan)

"""
Please create an endpoint that accepts a query string, e.g., "what happens if I steal 
from the Sept?" and returns a JSON response serialized from the Pydantic Output class.
"""
@app.get("/live")
async def live() -> Dict[str, str]:
    return {"status": "ok"}

@app.get("/ready")
async def ready() -> Dict[str, str]:
    if hasattr(app.state, "ready_for_queries") and app.state.ready_for_queries:
        return {"status": "ok"}
    return {"status": "not ready"}

@app.post("/query", response_model=Output)
async def query(input: Input) -> Output:
    qdrant_service = app.state.qdrant_service
    return qdrant_service.query(input.query)