from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.utils import Output, DocumentService, QdrantService
import os

# Initialize FastAPI app
app = FastAPI(
    title="Westeros Laws API",
    description="API for querying the laws of the Seven Kingdoms",
    version="1.0.0",
)

# Add CORS middleware to allow cross-origin requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize services
doc_service = DocumentService()
qdrant_service = QdrantService(k=3)  # Return top 3 most relevant results

# Load documents and initialize index on startup
@app.on_event("startup")
async def startup_event():
    try:
        # Check if OpenAI API key is set
        if "OPENAI_API_KEY" not in os.environ:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        # Load documents from PDF
        docs = doc_service.create_documents()
        
        # Initialize Qdrant service
        qdrant_service.connect()
        
        # Load documents into the index
        qdrant_service.load(docs)
        
        print("Successfully loaded documents and initialized index")
    except Exception as e:
        print(f"Error during startup: {str(e)}")
        # We don't want to crash the app, but we'll log the error

# Request model
class QueryRequest(BaseModel):
    query: str

# Endpoint for querying the laws
@app.post("/query", response_model=Output)
async def query_laws(request: QueryRequest):
    """
    Query the laws of the Seven Kingdoms.
    
    This endpoint accepts a query string and returns a response with relevant citations.
    
    Example query: "What happens if I steal from the Sept?"
    """
    try:
        if not request.query or request.query.strip() == "":
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Process the query
        result = qdrant_service.query(request.query)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

# Simple GET endpoint for testing
@app.get("/query", response_model=Output)
async def query_laws_get(query: str = Query(..., description="The query string")):
    """
    Query the laws of the Seven Kingdoms using a GET request.
    
    This endpoint accepts a query string and returns a response with relevant citations.
    
    Example query: "What happens if I steal from the Sept?"
    """
    try:
        if not query or query.strip() == "":
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Process the query
        result = qdrant_service.query(query)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)