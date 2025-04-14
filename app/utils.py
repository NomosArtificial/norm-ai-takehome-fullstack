from pydantic import BaseModel
import qdrant_client
# Fix import path for QdrantVectorStore based on installed packages
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
# Fix import paths to be consistent with the package structure
from llama_index.core.schema import Document
from llama_index.core import (
    VectorStoreIndex,
    ServiceContext,
)
from llama_index.core.query_engine import CitationQueryEngine
from dataclasses import dataclass
import os
import re
import PyPDF2
from typing import List, Dict, Any, Optional

key = os.environ['OPENAI_API_KEY']

@dataclass
class Input:
    query: str
    file_path: str

@dataclass
class Citation:
    source: str
    text: str

class Output(BaseModel):
    query: str
    response: str
    citations: list[Citation]

class DocumentService:
    """
    Service to load the PDF and extract its contents.
    Creates Document objects that can be used with QdrantService.
    """
    
    def __init__(self, pdf_path: str = "docs/laws.pdf"):
        self.pdf_path = pdf_path
    
    def create_documents(self) -> List[Document]:
        """
        Extract text from PDF and create Document objects with appropriate metadata.
        Each Document represents a law or subsection with hierarchical metadata.
        """
        # Extract raw text from PDF
        raw_text = self._extract_text_from_pdf()
        
        # Parse the text into structured sections
        sections = self._parse_text_into_sections(raw_text)
        
        # Create Document objects from the parsed sections
        documents = self._create_documents_from_sections(sections)
        
        return documents
    
    def _extract_text_from_pdf(self) -> str:
        """Extract text from PDF file."""
        text = ""
        try:
            with open(self.pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")
    
    def _parse_text_into_sections(self, text: str) -> Dict[str, Any]:
        """
        Parse the raw text into a hierarchical structure of sections.
        Returns a dictionary representing the hierarchical structure.
        """
        # Split text into lines and remove empty lines
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Initialize the root of our hierarchical structure
        root = {"title": "Laws of the Seven Kingdoms", "content": "", "children": {}}
        current_path = []
        
        # Regular expressions for section patterns
        section_pattern = re.compile(r'^(\d+)\.(.*)$')
        subsection_pattern = re.compile(r'^(\d+\.\d+)\.(.*)$')
        subsubsection_pattern = re.compile(r'^(\d+\.\d+\.\d+)\.(.*)$')
        
        current_section = None
        current_subsection = None
        current_subsubsection = None
        
        for line in lines:
            # Check if line is a main section (e.g., "1.Peace")
            section_match = section_pattern.match(line)
            if section_match:
                section_num, section_title = section_match.groups()
                section_num = section_num.strip()
                section_title = section_title.strip()
                
                # Create new section
                current_section = {"title": section_title, "content": "", "children": {}}
                root["children"][section_num] = current_section
                current_subsection = None
                current_subsubsection = None
                continue
            
            # Check if line is a subsection (e.g., "1.1.The law requires...")
            subsection_match = subsection_pattern.match(line)
            if subsection_match and current_section is not None:
                subsection_num, subsection_content = subsection_match.groups()
                subsection_num = subsection_num.strip()
                subsection_content = subsection_content.strip()
                
                # Create new subsection
                current_subsection = {"title": "", "content": subsection_content, "children": {}}
                section_num = subsection_num.split('.')[0]
                current_section["children"][subsection_num] = current_subsection
                current_subsubsection = None
                continue
            
            # Check if line is a subsubsection (e.g., "1.1.1.However, the law...")
            subsubsection_match = subsubsection_pattern.match(line)
            if subsubsection_match and current_subsection is not None:
                subsubsection_num, subsubsection_content = subsubsection_match.groups()
                subsubsection_num = subsubsection_num.strip()
                subsubsection_content = subsubsection_content.strip()
                
                # Create new subsubsection
                current_subsubsection = {"title": "", "content": subsubsection_content}
                subsection_num = '.'.join(subsubsection_num.split('.')[:2])
                current_subsection["children"][subsubsection_num] = current_subsubsection
                continue
            
            # If not a section header, append to current content
            if current_subsubsection is not None:
                current_subsubsection["content"] += " " + line
            elif current_subsection is not None:
                current_subsection["content"] += " " + line
            elif current_section is not None:
                current_section["content"] += " " + line
            else:
                root["content"] += " " + line
        
        return root
    
    def _create_documents_from_sections(self, root: Dict[str, Any]) -> List[Document]:
        """
        Create Document objects from the parsed sections.
        Each Document represents a law or subsection.
        """
        documents = []
        
        # Process main sections
        for section_num, section in root["children"].items():
            section_title = section["title"]
            section_content = section["content"].strip()
            
            # Create document for the main section if it has content
            if section_content:
                doc = Document(
                    text=section_content,
                    metadata={
                        "section": section_num,
                        "title": section_title,
                        "path": f"{section_num}. {section_title}"
                    }
                )
                documents.append(doc)
            
            # Process subsections
            for subsection_num, subsection in section["children"].items():
                subsection_content = subsection["content"].strip()
                
                # Create document for the subsection
                if subsection_content:
                    doc = Document(
                        text=subsection_content,
                        metadata={
                            "section": subsection_num,
                            "title": section_title,
                            "path": f"{section_num}. {section_title} > {subsection_num}."
                        }
                    )
                    documents.append(doc)
                
                # Process subsubsections
                for subsubsection_num, subsubsection in subsection["children"].items():
                    subsubsection_content = subsubsection["content"].strip()
                    
                    # Create document for the subsubsection
                    if subsubsection_content:
                        doc = Document(
                            text=subsubsection_content,
                            metadata={
                                "section": subsubsection_num,
                                "title": section_title,
                                "path": f"{section_num}. {section_title} > {subsection_num}. > {subsubsection_num}."
                            }
                        )
                        documents.append(doc)
        
        return documents

class QdrantService:
    def __init__(self, k: int = 2):
        self.index = None
        self.k = k
    
    def connect(self) -> None:
        try:
            # Initialize QdrantClient with minimal parameters to avoid compatibility issues
            client = qdrant_client.QdrantClient(location=":memory:")
            
            # Monkey patch OpenAI client creation at a lower level
            # We need to patch the actual client initialization in the OpenAI library
            
            # First, import the necessary modules
            from openai import OpenAI as OpenAIClient
            from openai._base_client import SyncHttpxClientWrapper
            
            # Save the original initialize methods
            original_openai_init = OpenAIClient.__init__
            original_httpx_wrapper_init = SyncHttpxClientWrapper.__init__
            
            # Create patched initialization functions
            def patched_openai_init(self, *args, **kwargs):
                # Remove 'proxies' if it exists
                if 'proxies' in kwargs:
                    print("DEBUG - Removing 'proxies' from OpenAIClient.__init__")
                    del kwargs['proxies']
                return original_openai_init(self, *args, **kwargs)
            
            def patched_httpx_wrapper_init(self, *args, **kwargs):
                # Remove 'proxies' if it exists
                if 'proxies' in kwargs:
                    print("DEBUG - Removing 'proxies' from SyncHttpxClientWrapper.__init__")
                    del kwargs['proxies']
                return original_httpx_wrapper_init(self, *args, **kwargs)
            
            # Apply the patches
            OpenAIClient.__init__ = patched_openai_init
            SyncHttpxClientWrapper.__init__ = patched_httpx_wrapper_init
            
            # Also apply our previous patches
            # Patch OpenAIEmbedding
            original_get_credential_kwargs = OpenAIEmbedding._get_credential_kwargs
            
            def patched_get_credential_kwargs(self):
                kwargs = original_get_credential_kwargs(self)
                print(f"DEBUG - OpenAIEmbedding credential kwargs: {kwargs}")
                # Remove 'proxies' if it exists
                if 'proxies' in kwargs:
                    print("DEBUG - Removing 'proxies' parameter")
                    del kwargs['proxies']
                return kwargs
            
            # Apply the monkey patch
            OpenAIEmbedding._get_credential_kwargs = patched_get_credential_kwargs
            
            # Patch OpenAI LLM
            original_llm_get_credential_kwargs = OpenAI._get_credential_kwargs
            
            def patched_llm_get_credential_kwargs(self):
                kwargs = original_llm_get_credential_kwargs(self)
                # Remove 'proxies' if it exists in LLM kwargs
                if 'proxies' in kwargs:
                    print("DEBUG - Removing 'proxies' parameter from LLM")
                    del kwargs['proxies']
                return kwargs
            
            # Apply the LLM monkey patch
            OpenAI._get_credential_kwargs = patched_llm_get_credential_kwargs
            
            # Create embedding model with minimal parameters
            embed_model = OpenAIEmbedding(
                api_key=key,
                model="text-embedding-ada-002"
            )
            
            # Create LLM with minimal parameters
            llm_model = OpenAI(
                api_key=key,
                model="gpt-4"
            )
            
            # Create a service context with the embedding model and LLM
            service_context = ServiceContext.from_defaults(
                embed_model=embed_model,
                llm=llm_model
            )
            
            # Initialize QdrantVectorStore with minimal parameters
            vstore = QdrantVectorStore(client=client, collection_name='temp')
            
            # Create the index from the vector store
            self.index = VectorStoreIndex.from_vector_store(
                vector_store=vstore,
                service_context=service_context
            )
        except Exception as e:
            # Print detailed error information for debugging
            import traceback
            print(f"Error in connect(): {str(e)}")
            print(traceback.format_exc())
            raise
    
    def load(self, docs: List[Document]):
        try:
            self.index.insert_nodes(docs)
        except Exception as e:
            # Print detailed error information for debugging
            import traceback
            print(f"Error in load(): {str(e)}")
            print(traceback.format_exc())
            raise
    
    def query(self, query_str: str) -> Output:
        """
        Initialize the CitationQueryEngine, run the query, and return
        the result as a pydantic Output class.
        """
        if not self.index:
            raise ValueError("Index not initialized. Call connect() first.")
        
        # Initialize the CitationQueryEngine with the specified number of results (k)
        query_engine = CitationQueryEngine.from_args(
            self.index,
            similarity_top_k=self.k,
            # Use tree_summarize to generate a coherent response from multiple sources
            response_mode="tree_summarize"
        )
        
        # Run the query
        response = query_engine.query(query_str)
        
        # Extract the response text
        response_text = str(response)
        
        # Extract citations from source nodes
        citations = []
        if hasattr(response, 'source_nodes'):
            for node in response.source_nodes:
                source = node.metadata.get("path", "Unknown")
                text = node.text
                citations.append(Citation(source=source, text=text))
        
        # Create and return the Output object
        output = Output(
            query=query_str,
            response=response_text,
            citations=citations
        )
        
        return output

if __name__ == "__main__":
    # Example workflow
    doc_service = DocumentService()  # implemented
    docs = doc_service.create_documents()  # implemented
    
    index = QdrantService()  # implemented
    index.connect()  # implemented
    index.load(docs)  # implemented
    
    result = index.query("what happens if I steal?")  # implemented
    print(result)
