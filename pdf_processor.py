import PyPDF2
import io
import re
from typing import List, Dict
from datetime import datetime
from config import config

class PDFProcessor:
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or config.CHUNK_OVERLAP
    
    def extract_text_from_pdf(self, file_bytes: bytes) -> str:
        """Extract text from PDF file bytes"""
        try:
            pdf_file = io.BytesIO(file_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Page {page_num + 1} ---\n"
                    text += page_text
            
            return self.clean_text(text)
        
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")
    
    def clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might cause issues
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)]', ' ', text)
        # Remove extra spaces
        text = re.sub(r' +', ' ', text)
        return text.strip()
    
    def chunk_text(self, text: str) -> List[Dict]:
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = ' '.join(chunk_words)
            
            # Extract page number if available
            page_match = re.search(r'--- Page (\d+) ---', chunk_text)
            page_number = int(page_match.group(1)) if page_match else None
            
            # Clean page markers from chunk text
            chunk_text = re.sub(r'--- Page \d+ ---', '', chunk_text).strip()
            
            if len(chunk_text) > 50:  # Only keep substantial chunks
                chunks.append({
                    'content': chunk_text,
                    'chunk_index': len(chunks),
                    'page_number': page_number,
                    'word_count': len(chunk_words)
                })
        
        return chunks
    
    def process_pdf(self, file_bytes: bytes, filename: str) -> Dict:
        """Complete PDF processing pipeline"""
        try:
            # Extract text
            text = self.extract_text_from_pdf(file_bytes)
            
            if not text or len(text.strip()) < 50:
                raise Exception("No substantial text found in PDF")
            
            # Create chunks
            chunks = self.chunk_text(text)
            
            if not chunks:
                raise Exception("No valid chunks created from PDF")
            
            # Add metadata to chunks
            timestamp = datetime.utcnow().isoformat()
            for chunk in chunks:
                chunk.update({
                    'source_file': filename,
                    'upload_timestamp': timestamp,
                    'document_type': 'pdf'
                })
            
            return {
                'success': True,
                'chunks': chunks,
                'total_chunks': len(chunks),
                'total_words': len(text.split()),
                'filename': filename
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'filename': filename
            }