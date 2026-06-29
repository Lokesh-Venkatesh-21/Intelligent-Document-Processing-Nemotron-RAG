import os
import shutil
import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json

from parser import extract_chunks_from_pdf
from vector_store import SimpleVectorStore

app = FastAPI(title="Nemotron IDP RAG Dashboard")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Persistent DB instance
vector_store = SimpleVectorStore()

# Global state to keep the API key in memory if not set in env
MEMORY_API_KEY = os.environ.get("NVIDIA_API_KEY", "")

class ConfigUpdate(BaseModel):
    api_key: str

class ChatQuery(BaseModel):
    query: str
    api_key: Optional[str] = None

def get_api_key(provided_key: Optional[str] = None) -> str:
    """Helper to resolve the API Key."""
    key = provided_key or MEMORY_API_KEY or os.environ.get("NVIDIA_API_KEY", "")
    if not key:
        raise HTTPException(
            status_code=400,
            detail="NVIDIA API Key is missing. Please set it in the Settings panel."
        )
    return key

@app.post("/api/config")
def update_config(config: ConfigUpdate):
    global MEMORY_API_KEY
    if not config.api_key.startswith("nvapi-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid API Key format. NVIDIA API Keys must start with 'nvapi-'"
        )
    MEMORY_API_KEY = config.api_key
    return {"status": "success", "message": "NVIDIA API Key updated successfully."}

@app.get("/api/config/status")
def get_config_status():
    has_key = bool(MEMORY_API_KEY or os.environ.get("NVIDIA_API_KEY"))
    return {"has_key": has_key}

@app.get("/api/documents")
def list_documents():
    """Lists all files stored in the vector database."""
    files = {}
    for chunk in vector_store.chunks:
        src = chunk["metadata"]["source"]
        files[src] = files.get(src, 0) + 1
        
    return {
        "documents": [{"filename": name, "chunks": count} for name, count in files.items()],
        "total_chunks": len(vector_store.chunks)
    }

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...), api_key: Optional[str] = Form(None)):
    resolved_key = get_api_key(api_key)
    
    os.makedirs("temp_uploads", exist_ok=True)
    total_parsed_chunks = 0
    uploaded_files = []
    
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            continue
            
        temp_path = f"temp_uploads/{uuid.uuid4()}_{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        try:
            # Extract and chunk
            chunks = extract_chunks_from_pdf(temp_path)
            if chunks:
                # Add embeddings
                vector_store.add_documents(chunks, resolved_key)
                total_parsed_chunks += len(chunks)
                uploaded_files.append(file.filename)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process {file.filename}: {str(e)}"
            )
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    return {
        "status": "success",
        "processed_files": uploaded_files,
        "new_chunks": total_parsed_chunks,
        "total_chunks": len(vector_store.chunks)
    }

@app.post("/api/clear")
def clear_db():
    vector_store.clear()
    return {"status": "success", "message": "Vector database cleared."}

@app.post("/api/chat")
async def chat_rag(payload: ChatQuery):
    resolved_key = get_api_key(payload.api_key)
    
    # 1. Search vector database
    search_results = vector_store.similarity_search(payload.query, resolved_key, k=5)
    
    # 2. Format context and citations
    context_blocks = []
    citations = []
    
    for idx, res in enumerate(search_results):
        chunk = res["chunk"]
        source = chunk["metadata"]["source"]
        page = chunk["metadata"]["page"]
        citation_id = idx + 1
        
        context_blocks.append(
            f"--- Context Segment [{citation_id}] ---\n"
            f"Source: {source} (Page {page})\n"
            f"Content: {chunk['text']}\n"
        )
        citations.append({
            "id": citation_id,
            "source": source,
            "page": page,
            "text": chunk["text"]
        })
        
    context_str = "\n".join(context_blocks)
    
    # 3. Create instruction prompt for Nemotron
    system_prompt = (
        "You are an expert AI assistant specialized in analyzing business, economic, and technical documents.\n"
        "Your task is to answer the user's question accurately using ONLY the provided document context segments.\n"
        "For each fact or claim you make in your answer, you MUST cite the context segment it comes from by using the exact format [Citation ID] at the end of the sentence or clause.\n"
        "Do not write citations in any other format (such as 'according to source 1' or markdown links). Use only bracketed numbers matching the Segment ID, e.g. [1] or [2].\n"
        "If the context does not contain enough information to answer the question, state that you cannot answer based on the provided documents. Do not make up information."
    )
    
    user_prompt = (
        f"Context segments:\n{context_str}\n\n"
        f"Question: {payload.query}\n\n"
        f"Grounded Answer:"
    )
    
    # 4. Stream response from Nemotron
    async def response_generator():
        client = vector_store.get_client(resolved_key)
        try:
            # Yield metadata/citations first
            yield f"citations:{json.dumps(citations)}\n\n"
            
            stream = client.chat.completions.create(
                model="nvidia/llama-3.3-nemotron-70b-instruct",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                top_p=0.7,
                max_tokens=1500,
                stream=True
            )
            
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield f"text:{content}\n\n"
                    
        except Exception as e:
            yield f"error:{str(e)}\n\n"
            
    return StreamingResponse(response_generator(), media_type="text/event-stream")

# Mount frontend
os.makedirs("static", exist_ok=True)

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

app.mount("/", StaticFiles(directory="static"), name="static")
