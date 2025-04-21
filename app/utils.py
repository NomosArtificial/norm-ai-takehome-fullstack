"""Core utilities for the QA system."""
from dataclasses import dataclass
import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel
import pdfplumber
import qdrant_client
import re

from llama_index.core import Document, Settings, VectorStoreIndex
from llama_index.core.query_engine import CitationQueryEngine
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.qdrant import QdrantVectorStore


# Get API key from environment
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']


@dataclass
class Input:
    """Input query for the QA system."""
    query: str


@dataclass
class Citation:
    """Citation from a source document."""
    source: str
    text: str


class Output(BaseModel):
    """Output from the QA system."""
    query: str
    response: str
    citations: List[Citation]


class DocumentService:
    """Service for processing and extracting content from PDF documents."""

    def __init__(self, path_to_source: str | Path) -> None:
        """Initialize with path to source document."""
        self.path_to_source = Path(path_to_source)

    def create_documents(self) -> List[Document]:
        """
        Extract content from PDF and create documents.
        
        Returns:
            List of Document objects with content and metadata.
        """
        docs: List[Document] = []
        with pdfplumber.open(self.path_to_source) as pdf:
            current_section: Optional[str] = None
            current_text: str = ""
            
            for page_num, page in enumerate(pdf.pages, 1):
                # Get words with their positions and font information
                words = page.extract_words(extra_attrs=['fontname'])
                if not words:
                    continue
                
                # Sort words by y-coordinate (top to bottom) and x-coordinate (left to right)
                words.sort(key=lambda w: (w['top'], w['x0']))
                
                # Process words line by line
                current_line: List[dict] = []
                for word in words:
                    # If this is the first word of a new line
                    if not current_line or word['top'] > current_line[-1]['bottom']:
                        # Process the previous line if it exists
                        if current_line:
                            line_text = " ".join(w['text'] for w in current_line)
                            line_text = line_text.strip()
                            if re.match(r'Citations', line_text):
                                current_line = []
                                break
                            
                            # Check if this line starts with a section number
                            section_match = re.match(r'^(\d+(\.\d+)*\.?)\s', line_text)
                            if section_match:
                                is_bold = any(
                                    w.get('fontname', '').lower().find('bold') != -1 
                                    for w in current_line[:1]
                                )
                                if is_bold:
                                    # If we have a previous section, save it
                                    if current_section and current_text.strip():
                                        doc = Document(
                                            metadata={"Section": current_section},
                                            text=current_text.strip()
                                        )
                                        docs.append(doc)
                                    
                                    # Start new section
                                    current_section = line_text[len(section_match.group(0)):].strip()
                                    current_text = ""
                                else:
                                    # Not a section header, add to current section
                                    if current_section:
                                        # Remove the section number from the text
                                        line_text = line_text[len(section_match.group(0)):].strip()
                                        current_text += "\n" + line_text
                            else:
                                # Add to current section's text
                                if current_section:
                                    current_text += "\n" + line_text
                        
                        # Start new line
                        current_line = [word]
                    else:
                        # Same line, add to current line
                        current_line.append(word)
                
                # Process the last line
                if current_line:
                    line_text = " ".join(w['text'] for w in current_line)
                    line_text = line_text.strip()
                    
                    section_match = re.match(r'^(\d+(\.\d+)*\.?)\s', line_text)
                    if section_match:
                        is_bold = any(
                            w.get('fontname', '').lower().find('bold') != -1 
                            for w in current_line[:1]
                        )
                        
                        if is_bold:
                            # Save previous section if it exists
                            if current_section and current_text.strip():
                                doc = Document(
                                    metadata={"Section": current_section},
                                    text=current_text.strip()
                                )
                                docs.append(doc)
                            
                            # Start new section
                            current_section = line_text[len(section_match.group(0)):].strip()
                            current_text = ""
                        else:
                            # Not a section header, add to current section
                            if current_section:
                                # Remove the section number from the text
                                line_text = line_text[len(section_match.group(0)):].strip()
                                current_text += "\n" + line_text
                    else:
                        # Add to current section's text
                        if current_section:
                            current_text += "\n" + line_text
            
            # Add the last section if it exists
            if current_section and current_text.strip():
                doc = Document(
                    metadata={"Section": current_section},
                    text=current_text.strip()
                )
                docs.append(doc)
        
        return docs


class QdrantService:
    """Service for vector storage and retrieval using Qdrant."""

    def __init__(self, k: int = 2) -> None:
        """Initialize with number of similar vectors to retrieve."""
        self.index: Optional[VectorStoreIndex] = None
        self.k = k
    
    def connect(self) -> None:
        """Initialize connection to Qdrant and set up the index."""
        client = qdrant_client.QdrantClient(location=":memory:")
        vstore = QdrantVectorStore(client=client, collection_name='temp')

        Settings.embed_model = OpenAIEmbedding()
        Settings.llm = OpenAI(api_key=OPENAI_API_KEY, model="gpt-4")

        self.index = VectorStoreIndex.from_vector_store(
            vector_store=vstore,
            embed_model=OpenAIEmbedding()
        )

    def load(self, docs: List[Document]) -> None:
        """
        Load documents into the vector store.
        
        Args:
            docs: List of documents to index
        
        Raises:
            ValueError: If index is not initialized
        """
        if self.index is None:
            raise ValueError("Index not initialized. Call connect() first.")
        self.index.insert_nodes(docs)
    
    def query(self, query_str: str) -> Output:
        """
        Query the vector store and return relevant results.
        
        Args:
            query_str: Query string to process
        
        Returns:
            Output containing response and citations
        
        Raises:
            ValueError: If index is not initialized
        """
        if self.index is None:
            raise ValueError("Index not initialized. Call connect() first.")
            
        query_engine = CitationQueryEngine.from_args(
            self.index,
            similarity_top_k=self.k,
        )

        response = query_engine.query(query_str)
        citations = [
            Citation(source=node.metadata["Section"], text=node.text)
            for node in response.source_nodes
        ]
        
        return Output(
            query=query_str,
            response=response.response,
            citations=citations
        )


if __name__ == "__main__":
    # Example workflow
    pdf_path = Path(__file__).parent.parent / "docs" / "laws.pdf"
    doc_serivce = DocumentService(pdf_path) # implemented
    docs = doc_serivce.create_documents() # NOT implemented
    # for doc in docs:
    #     print("================")
    #     print(doc.metadata)
    #     print(doc.text)

    index = QdrantService() # implemented
    index.connect() # implemented
    index.load(docs) # implemented

    response = index.query("what happens if I steal from the Sept?")
    # print(response.response)
    # print(response.citations)





