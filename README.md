# Westeros Laws Query System

This repository contains a full-stack application that allows users to query the laws of the Seven Kingdoms from the fictional series "Game of Thrones". The application uses a FastAPI backend with llama-index for semantic search and a Next.js frontend.

## Features

- PDF processing to extract and structure laws
- Vector-based semantic search using llama-index and OpenAI embeddings
- Citation-based responses with references to specific laws
- Modern React frontend with Chakra UI
- Docker containerization for easy deployment

## Prerequisites

- Docker and Docker Compose
- OpenAI API key

## Setup and Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd norm-ai-takehome-fullstack
```

### 2. Set up environment variables

Create a `.env` file in the root directory with your OpenAI API key:

```
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Build and run with Docker Compose

```bash
docker-compose up --build
```

This will:
- Build the backend container
- Build the frontend container
- Start both services
- Connect them together

### 4. Access the application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Manual Setup (without Docker)

### Backend

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Set the OpenAI API key:
```bash
export OPENAI_API_KEY=your_openai_api_key_here
```

3. Run the FastAPI server:
```bash
uvicorn app.main:app --reload
```

### Frontend

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
pnpm install
```

3. Run the development server:
```bash
pnpm dev
```

## API Usage

The API provides the following endpoints:

### POST /query

Send a query to search the laws.

Request body:
```json
{
  "query": "What happens if I steal from the Sept?"
}
```

Response:
```json
{
  "query": "What happens if I steal from the Sept?",
  "response": "Stealing from a sept is considered a serious offense in the Seven Kingdoms...",
  "citations": [
    {
      "source": "6. Thievery > 6.3.",
      "text": "Those who steal from a sept can be considered to have stolen from the gods, and thus receive a harsher punishment."
    }
  ]
}
```

### GET /query

Same as POST /query but using query parameters.

Example: `GET /query?query=What%20happens%20if%20I%20steal%20from%20the%20Sept%3F`

### GET /health

Health check endpoint.

## Project Structure

- `app/`: Backend code
  - `main.py`: FastAPI application and endpoints
  - `utils.py`: Core functionality (DocumentService, QdrantService)
- `docs/`: Documentation and data files
  - `laws.pdf`: PDF containing the laws of the Seven Kingdoms
- `frontend/`: Next.js frontend application
  - `app/`: Next.js app directory
  - `components/`: React components
  - `services/`: API services
- `Dockerfile`: Backend Docker configuration
- `frontend/Dockerfile.frontend`: Frontend Docker configuration
- `docker-compose.yml`: Docker Compose configuration

## Design Choices and Assumptions

1. **PDF Processing**: The application uses PyPDF2 to extract text from the PDF and parses it into a hierarchical structure based on the numbering system (e.g., 1., 1.1., 1.1.1.).

2. **Vector Search**: The application uses llama-index with OpenAI embeddings to perform semantic search on the laws. This allows for natural language queries and returns the most relevant laws.

3. **Citation Engine**: The application uses llama-index's CitationQueryEngine to generate responses with citations to specific laws.

4. **Frontend Design**: The frontend is designed to be simple and intuitive, with a search box and results display. The results include both the AI-generated response and the citations to specific laws.

5. **Docker Containerization**: The application is containerized using Docker to make it easy to deploy and run in any environment.

## Limitations and Future Improvements

1. **PDF Parsing**: The current PDF parsing logic is specific to the format of the provided laws.pdf file. A more robust solution would handle different PDF formats.

2. **Error Handling**: More comprehensive error handling could be added, especially for edge cases in the PDF parsing.

3. **Authentication**: The application does not currently include authentication. This could be added for production use.

4. **Caching**: Response caching could be implemented to improve performance for repeated queries.

5. **Testing**: Comprehensive unit and integration tests could be added to ensure reliability.
