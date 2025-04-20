from pydantic import BaseModel
import qdrant_client
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core import (
    VectorStoreIndex,
    Settings,
    Document,
)
from llama_index.core.query_engine import CitationQueryEngine
from llama_index.core import Settings
from dataclasses import dataclass
import os
from pathlib import Path
import pdfplumber
import re
from typing import List, Optional

key = os.environ['OPENAI_API_KEY']

@dataclass
class Input:
    query: str
    # file_path: str

@dataclass
class Citation:
    source: str
    text: str

class Output(BaseModel):
    query: str
    response: str
    citations: List[Citation]

class DocumentService:

    """
    Update this service to load the pdf and extract its contents.
    The example code below will help with the data structured required
    when using the QdrantService.load() method below. Note: for this
    exercise, ignore the subtle difference between llama-index's 
    Document and Node classes (i.e, treat them as interchangeable).

    # example code
    def create_documents() -> list[Document]:

        docs = [
            Document(
                metadata={"Section": "Law 1"},
                text="Theft is punishable by hanging",
            ),
            Document(
                metadata={"Section": "Law 2"},
                text="Tax evasion is punishable by banishment.",
            ),
        ]

        return docs

     """
    def __init__(self, path_to_pdf: str | Path):
        self.path_to_pdf = Path(path_to_pdf)

    def create_documents(self) -> List[Document]:
        docs: List[Document] = []
        with pdfplumber.open(self.path_to_pdf) as pdf:
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
                                is_bold = any(w.get('fontname', '').lower().find('bold') != -1 for w in current_line[:1])
                                if is_bold:
                                    # If we have a previous section, save it
                                    if current_section and current_text.strip():
                                        doc = Document(
                                            metadata={
                                                "Section": current_section
                                            },
                                            text=current_text.strip()
                                        )
                                        docs.append(doc)
                                    
                                    # Start new section
                                    # Remove the section number from the text
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
                        # Check if the section number is bold
                        is_bold = any(w.get('fontname', '').lower().find('bold') != -1 for w in current_line[:1])
                        
                        if is_bold:
                            # Save previous section if it exists
                            if current_section and current_text.strip():
                                doc = Document(
                                    metadata={
                                        "Section": current_section
                                    },
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
                    metadata={
                        "Section": current_section
                    },
                    text=current_text.strip()
                )
                docs.append(doc)
        
        return docs

class QdrantService:
    def __init__(self, k: int = 2):
        self.index: Optional[VectorStoreIndex] = None
        self.k = k
    
    def connect(self) -> None:
        client = qdrant_client.QdrantClient(location=":memory:")
                
        vstore = QdrantVectorStore(client=client, collection_name='temp')

        Settings.embed_model = OpenAIEmbedding()
        Settings.llm = OpenAI(api_key=key, model="gpt-4")
        
        # storage_context = StorageContext.from_defaults(vector_store=vector_store)

        self.index = VectorStoreIndex.from_vector_store(
            vector_store=vstore, 
            embed_model=OpenAIEmbedding()
        )

    def load(self, docs: List[Document]) -> None:
        if self.index is None:
            raise ValueError("Index not initialized. Call connect() first.")
        self.index.insert_nodes(docs)
    
    def query(self, query_str: str) -> Output:

        """
        This method needs to initialize the query engine, run the query, and return
        the result as a pydantic Output class. This is what will be returned as
        JSON via the FastAPI endpount. Fee free to do this however you'd like, but
        a its worth noting that the llama-index package has a CitationQueryEngine...

        Also, be sure to make use of self.k (the number of vectors to return based
        on semantic similarity).

        # Example output object
        citations = [
            Citation(source="Law 1", text="Theft is punishable by hanging"),
            Citation(source="Law 2", text="Tax evasion is punishable by banishment."),
        ]

        output = Output(
            query=query_str, 
            response=response_text, 
            citations=citations
            )
        
        return output

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





