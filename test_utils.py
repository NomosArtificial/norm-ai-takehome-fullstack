"""
Test script for DocumentService and QdrantService
"""

import os
import sys
from app.utils import DocumentService, QdrantService

def test_document_service():
    """Test the DocumentService class"""
    print("Testing DocumentService...")
    
    # Initialize DocumentService
    doc_service = DocumentService()
    
    # Create documents
    try:
        docs = doc_service.create_documents()
        print(f"Successfully created {len(docs)} documents")
        
        # Print some sample documents
        print("\nSample documents:")
        for i, doc in enumerate(docs[:3]):  # Print first 3 documents
            print(f"\nDocument {i+1}:")
            print(f"  Section: {doc.metadata.get('section', 'N/A')}")
            print(f"  Title: {doc.metadata.get('title', 'N/A')}")
            print(f"  Path: {doc.metadata.get('path', 'N/A')}")
            print(f"  Text: {doc.text[:100]}...")  # Print first 100 chars of text
        
        return docs
    except Exception as e:
        print(f"Error creating documents: {str(e)}")
        return None

def test_qdrant_service(docs):
    """Test the QdrantService class"""
    print("\nTesting QdrantService...")
    
    if not docs:
        print("No documents to test with")
        return
    
    # Initialize QdrantService
    qdrant_service = QdrantService(k=3)  # Return top 3 results
    
    try:
        # Connect to Qdrant
        print("Connecting to Qdrant...")
        qdrant_service.connect()
        
        # Load documents
        print("Loading documents...")
        qdrant_service.load(docs)
        
        # Test queries
        test_queries = [
            "What happens if I steal?",
            "What are the laws about slavery?",
            "How are trials conducted?",
            "What happens if I steal from the Sept?"
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            try:
                result = qdrant_service.query(query)
                print(f"Response: {result.response[:150]}...")  # Print first 150 chars
                print("Citations:")
                for i, citation in enumerate(result.citations):
                    print(f"  {i+1}. {citation.source}: {citation.text[:100]}...")
            except Exception as e:
                print(f"Error querying: {str(e)}")
    
    except Exception as e:
        print(f"Error in QdrantService: {str(e)}")

if __name__ == "__main__":
    # Check if OpenAI API key is set
    if "OPENAI_API_KEY" not in os.environ:
        print("Error: OPENAI_API_KEY environment variable is not set")
        print("Please set it with: export OPENAI_API_KEY=your_api_key")
        sys.exit(1)
    
    # Test DocumentService
    docs = test_document_service()
    
    # Test QdrantService
    test_qdrant_service(docs)