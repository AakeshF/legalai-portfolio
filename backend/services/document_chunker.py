"""
Document Chunking Service for Legal Documents

This service intelligently chunks legal documents while preserving structure,
context, and legal meaning. It handles various legal document formats and
ensures chunks maintain coherent legal concepts.
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import tiktoken
from nltk.tokenize import sent_tokenize, word_tokenize
import nltk

# Download required NLTK data
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")


@dataclass
class DocumentChunk:
    """Represents a chunk of a document with metadata"""

    content: str
    chunk_index: int
    start_char: int
    end_char: int
    tokens: int
    metadata: Dict

    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "chunk_index": self.chunk_index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "tokens": self.tokens,
            "metadata": self.metadata,
        }


class LegalDocumentChunker:
    """
    Intelligent document chunker for legal documents that preserves
    legal structure and meaning.
    """

    # Legal document section patterns
    SECTION_PATTERNS = [
        r"^(?:ARTICLE|Article)\s+[IVXLCDM]+\.?\s*[-–—]?\s*",  # Article I, Article II
        r"^(?:Section|SECTION|Sec\.?)\s+\d+\.?\d*\s*[-–—]?\s*",  # Section 1, Section 2.1
        r"^\d+\.\s+[A-Z]",  # 1. DEFINITIONS
        r"^[A-Z][A-Z\s]+:$",  # DEFINITIONS:
        r"^(?:WHEREAS|NOW, THEREFORE)",  # Contract preambles
        r"^(?:EXHIBIT|SCHEDULE|APPENDIX)\s+[A-Z0-9]+",  # Exhibit A, Schedule 1
    ]

    # Legal list indicators
    LIST_PATTERNS = [
        r"^\s*\([a-z]\)",  # (a), (b), (c)
        r"^\s*\([ivx]+\)",  # (i), (ii), (iii)
        r"^\s*\d+\.",  # 1., 2., 3.
        r"^\s*[a-z]\.",  # a., b., c.
    ]

    # Legal clause boundaries
    CLAUSE_BOUNDARIES = [
        r";\s*(?:and|or)\s*$",  # Semicolon with and/or
        r"\.\s*$",  # Period at end
        r":\s*$",  # Colon at end
    ]

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 100,
        min_chunk_size: int = 100,
        max_chunk_size: int = 1024,
        encoding_name: str = "cl100k_base",  # GPT-4 encoding
    ):
        """
        Initialize the chunker with configuration.

        Args:
            chunk_size: Target size for chunks in tokens
            chunk_overlap: Number of tokens to overlap between chunks
            min_chunk_size: Minimum chunk size in tokens
            max_chunk_size: Maximum chunk size in tokens
            encoding_name: Tokenizer encoding to use
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.tokenizer = tiktoken.get_encoding(encoding_name)

    def chunk_document(
        self,
        text: str,
        document_type: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> List[DocumentChunk]:
        """
        Chunk a legal document intelligently.

        Args:
            text: The document text to chunk
            document_type: Type of legal document (contract, brief, etc.)
            metadata: Additional metadata to include

        Returns:
            List of DocumentChunk objects
        """
        if not text or len(text.strip()) == 0:
            return []

        # Preprocess text
        text = self._preprocess_text(text)

        # Extract document structure
        sections = self._extract_sections(text)

        # Create chunks respecting structure
        chunks = []
        chunk_index = 0

        for section in sections:
            section_chunks = self._chunk_section(
                section["content"], section["metadata"], chunk_index
            )

            for chunk in section_chunks:
                # Add document-level metadata
                if metadata:
                    chunk.metadata.update(metadata)
                if document_type:
                    chunk.metadata["document_type"] = document_type

                chunks.append(chunk)
                chunk_index += 1

        # Apply overlap between chunks
        chunks = self._apply_overlap(chunks, text)

        return chunks

    def _preprocess_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)
        # Fix common OCR issues
        text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)  # Add space between camelCase
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(""", "'").replace(""", "'")
        return text.strip()

    def _extract_sections(self, text: str) -> List[Dict]:
        """Extract logical sections from the document"""
        sections = []
        current_section = {
            "content": "",
            "metadata": {"section_type": "preamble", "headers": []},
        }

        lines = text.split("\n")

        for i, line in enumerate(lines):
            # Check if this line is a section header
            is_header = False
            for pattern in self.SECTION_PATTERNS:
                if re.match(pattern, line.strip()):
                    # Save current section if it has content
                    if current_section["content"].strip():
                        sections.append(current_section)

                    # Start new section
                    current_section = {
                        "content": "",
                        "metadata": {
                            "section_type": "section",
                            "headers": [line.strip()],
                        },
                    }
                    is_header = True
                    break

            if not is_header:
                current_section["content"] += line + "\n"

        # Don't forget the last section
        if current_section["content"].strip():
            sections.append(current_section)

        # If no sections found, treat entire document as one section
        if not sections:
            sections = [
                {
                    "content": text,
                    "metadata": {"section_type": "document", "headers": []},
                }
            ]

        return sections

    def _chunk_section(
        self, section_text: str, section_metadata: Dict, start_index: int
    ) -> List[DocumentChunk]:
        """Chunk a section of text intelligently"""
        chunks = []

        # Split into sentences
        sentences = sent_tokenize(section_text)

        current_chunk = []
        current_tokens = 0
        chunk_start_char = 0

        for i, sentence in enumerate(sentences):
            sentence_tokens = len(self.tokenizer.encode(sentence))

            # Check if adding this sentence would exceed chunk size
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                # Create chunk
                chunk_text = " ".join(current_chunk)
                chunk = DocumentChunk(
                    content=chunk_text,
                    chunk_index=start_index + len(chunks),
                    start_char=chunk_start_char,
                    end_char=chunk_start_char + len(chunk_text),
                    tokens=current_tokens,
                    metadata=section_metadata.copy(),
                )
                chunks.append(chunk)

                # Start new chunk
                current_chunk = []
                current_tokens = 0
                chunk_start_char += len(chunk_text) + 1

            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_tokens += sentence_tokens

            # Check for legal boundaries that suggest chunk break
            if (
                self._is_legal_boundary(sentence)
                and current_tokens >= self.min_chunk_size
            ):
                chunk_text = " ".join(current_chunk)
                chunk = DocumentChunk(
                    content=chunk_text,
                    chunk_index=start_index + len(chunks),
                    start_char=chunk_start_char,
                    end_char=chunk_start_char + len(chunk_text),
                    tokens=current_tokens,
                    metadata=section_metadata.copy(),
                )
                chunks.append(chunk)

                current_chunk = []
                current_tokens = 0
                chunk_start_char += len(chunk_text) + 1

        # Handle remaining content
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk = DocumentChunk(
                content=chunk_text,
                chunk_index=start_index + len(chunks),
                start_char=chunk_start_char,
                end_char=chunk_start_char + len(chunk_text),
                tokens=current_tokens,
                metadata=section_metadata.copy(),
            )
            chunks.append(chunk)

        return chunks

    def _is_legal_boundary(self, text: str) -> bool:
        """Check if text represents a natural legal boundary"""
        text = text.strip()

        # Check for clause boundaries
        for pattern in self.CLAUSE_BOUNDARIES:
            if re.search(pattern, text):
                return True

        # Check for numbered sections
        if re.match(r"^\d+\.", text):
            return True

        # Check for definition endings
        if text.endswith("means") or text.endswith("shall mean"):
            return False  # Don't break before definition

        return False

    def _apply_overlap(
        self, chunks: List[DocumentChunk], original_text: str
    ) -> List[DocumentChunk]:
        """Apply overlap between consecutive chunks"""
        if len(chunks) <= 1 or self.chunk_overlap == 0:
            return chunks

        overlapped_chunks = []

        for i, chunk in enumerate(chunks):
            if i == 0:
                # First chunk - add overlap from next chunk
                if i + 1 < len(chunks):
                    next_chunk = chunks[i + 1]
                    overlap_text = self._get_overlap_text(
                        next_chunk.content, self.chunk_overlap, "start"
                    )
                    new_content = chunk.content + " " + overlap_text
                else:
                    new_content = chunk.content
            elif i == len(chunks) - 1:
                # Last chunk - add overlap from previous chunk
                prev_chunk = chunks[i - 1]
                overlap_text = self._get_overlap_text(
                    prev_chunk.content, self.chunk_overlap, "end"
                )
                new_content = overlap_text + " " + chunk.content
            else:
                # Middle chunks - add overlap from both sides
                prev_chunk = chunks[i - 1]
                next_chunk = chunks[i + 1]

                prev_overlap = self._get_overlap_text(
                    prev_chunk.content, self.chunk_overlap // 2, "end"
                )
                next_overlap = self._get_overlap_text(
                    next_chunk.content, self.chunk_overlap // 2, "start"
                )

                new_content = prev_overlap + " " + chunk.content + " " + next_overlap

            # Update chunk with overlapped content
            chunk.content = new_content.strip()
            chunk.tokens = len(self.tokenizer.encode(chunk.content))
            overlapped_chunks.append(chunk)

        return overlapped_chunks

    def _get_overlap_text(self, text: str, num_tokens: int, position: str) -> str:
        """Get overlap text from start or end of chunk"""
        tokens = self.tokenizer.encode(text)

        if position == "start":
            overlap_tokens = tokens[:num_tokens]
        else:  # end
            overlap_tokens = tokens[-num_tokens:]

        return self.tokenizer.decode(overlap_tokens)

    def estimate_chunks(self, text: str) -> int:
        """Estimate the number of chunks for a document"""
        total_tokens = len(self.tokenizer.encode(text))

        # Account for overlap
        effective_chunk_size = self.chunk_size - self.chunk_overlap
        estimated_chunks = (
            total_tokens + effective_chunk_size - 1
        ) // effective_chunk_size

        return max(1, estimated_chunks)
