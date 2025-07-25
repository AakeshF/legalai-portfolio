# memory_config.py - Memory optimization settings for the legal AI backend

import os
from typing import Dict, Any


class MemoryConfig:
    """Configuration for memory optimization across the application"""

    # Document processing limits
    MAX_FILE_SIZE_MB = 50  # Maximum file size for upload
    MAX_PDF_STREAMING_SIZE_MB = 10  # Files larger than this use streaming
    MAX_TEXT_EXTRACTION_CHARS = 5_000_000  # 5MB text limit per document
    PDF_BATCH_SIZE = 50  # Pages to process at once

    # AI context limits
    MAX_DOCUMENTS_IN_CONTEXT = 5  # Maximum documents to include in AI context
    MAX_CONTENT_PER_DOCUMENT = 10_000  # Characters per document in context
    MAX_MESSAGE_LENGTH = 20_000  # Maximum characters per message to AI

    # API token limits (to prevent excessive costs)
    MAX_TOKENS_PER_REQUEST = 4_000  # Maximum tokens in API response
    MAX_INPUT_TOKENS = 30_000  # Approximate maximum input tokens

    # Database query limits
    MAX_DOCUMENTS_PER_QUERY = 100  # Maximum documents returned in list queries
    MAX_CHAT_HISTORY_MESSAGES = 50  # Maximum chat messages to retrieve

    # Memory monitoring thresholds
    MEMORY_WARNING_THRESHOLD_MB = 1024  # Warn if process uses more than 1GB
    MEMORY_CRITICAL_THRESHOLD_MB = 2048  # Critical if process uses more than 2GB

    @staticmethod
    def get_memory_limits() -> Dict[str, Any]:
        """Get current memory limit configuration"""
        return {
            "file_limits": {
                "max_file_size_mb": MemoryConfig.MAX_FILE_SIZE_MB,
                "max_pdf_streaming_size_mb": MemoryConfig.MAX_PDF_STREAMING_SIZE_MB,
                "max_text_extraction_chars": MemoryConfig.MAX_TEXT_EXTRACTION_CHARS,
            },
            "ai_limits": {
                "max_documents_in_context": MemoryConfig.MAX_DOCUMENTS_IN_CONTEXT,
                "max_content_per_document": MemoryConfig.MAX_CONTENT_PER_DOCUMENT,
                "max_message_length": MemoryConfig.MAX_MESSAGE_LENGTH,
            },
            "api_limits": {
                "max_tokens_per_request": MemoryConfig.MAX_TOKENS_PER_REQUEST,
                "max_input_tokens": MemoryConfig.MAX_INPUT_TOKENS,
            },
            "db_limits": {
                "max_documents_per_query": MemoryConfig.MAX_DOCUMENTS_PER_QUERY,
                "max_chat_history_messages": MemoryConfig.MAX_CHAT_HISTORY_MESSAGES,
            },
        }

    @staticmethod
    def optimize_for_environment():
        """Adjust limits based on available system memory"""
        try:
            import psutil

            available_memory_mb = psutil.virtual_memory().available / (1024 * 1024)

            # Adjust limits if running on low memory system
            if available_memory_mb < 2048:  # Less than 2GB available
                MemoryConfig.MAX_DOCUMENTS_IN_CONTEXT = 3
                MemoryConfig.MAX_CONTENT_PER_DOCUMENT = 5_000
                MemoryConfig.PDF_BATCH_SIZE = 25
                print(
                    f"⚠️ Low memory detected ({available_memory_mb:.0f}MB). Applying conservative limits."
                )

            return available_memory_mb

        except ImportError:
            print("📊 psutil not available for memory monitoring")
            return None


# Initialize memory optimization on import
available_memory = MemoryConfig.optimize_for_environment()
if available_memory:
    print(f"💾 Memory configuration initialized. Available: {available_memory:.0f}MB")
