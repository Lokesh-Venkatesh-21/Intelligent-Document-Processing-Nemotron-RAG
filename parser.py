import os
import re
from pypdf import PdfReader

def extract_chunks_from_pdf(file_path: str, chunk_size: int = 800, chunk_overlap: int = 150):
    """
    Extracts text page-by-page from a PDF, chunking it with overlapping windows,
    preserving metadata for RAG citation mapping.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    filename = os.path.basename(file_path)
    reader = PdfReader(file_path)
    chunks = []
    
    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        text = page.extract_text() or ""
        
        # Clean extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        if not text:
            continue
            
        # Character-based sliding window chunking
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            
            # Adjust chunk boundaries to avoid cutting mid-word if possible
            if end < len(text):
                last_space = chunk_text.rfind(' ')
                if last_space > chunk_size // 2:
                    chunk_text = chunk_text[:last_space]
                    end = start + last_space
            
            chunks.append({
                "text": chunk_text.strip(),
                "metadata": {
                    "source": filename,
                    "page": page_num,
                    "length": len(chunk_text)
                }
            })
            
            start += (chunk_size - chunk_overlap)
            
    return chunks
