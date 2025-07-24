# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development
```bash
# Start the FastAPI development server
python start.py

# Install dependencies
pip install -r Requirements.txt

# Create/activate virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux
venv\Scripts\activate     # On Windows
```

### Testing
```bash
# Run API tests
python test_api.py

# Test specific endpoints manually
curl -X GET http://localhost:8000/health
```

### Database Management
```bash
# Check database status and tables
python check_db.py

# Run database migrations
python migrate_db.py

# Fix database issues
python fix_database_complete.py
```

## Architecture Overview

This is a FastAPI-based legal document analysis backend with the following key components:

### Core Services

1. **AIService** (`services/ai_service.py`): 
   - Integrates with [AI Provider] AI API for legal document analysis
   - Provides specialized analysis for different legal document types (contracts, immigration, family law, etc.)
   - Performs entity extraction, risk assessment, and generates actionable insights
   - Has fallback demo mode when API is unavailable

2. **DocumentProcessor** (`services/document_processor.py`):
   - Extracts text from PDF, DOCX, and TXT files
   - Manages document processing pipeline: upload → storage → extraction → AI analysis
   - Updates document status throughout processing lifecycle

3. **MCPManager** (`services/mcp_manager.py`):
   - Manages Model Context Protocol servers for external data integration
   - Supports filesystem, email, calendar, and document management system connections

### API Structure

The main FastAPI application (`main.py`) exposes:
- `/api/documents/*` - Document upload, retrieval, deletion, and reprocessing
- `/api/chat` - AI chat interface with document context
- `/api/mcp/*` - MCP server management

### Database Schema

Three main SQLAlchemy models (`models.py`):
- `Document`: Stores uploaded documents with metadata, content, and AI analysis
- `ChatSession`: Manages conversation sessions
- `ChatMessage`: Stores chat history with session context

### Key Configuration

Configuration is managed via `config.py` using Pydantic Settings:
- Database URL (defaults to SQLite, supports PostgreSQL)
- API keys ([AI Provider] AI, JWT secret)
- Upload settings (50MB file limit, upload directory)
- CORS configuration for frontend integration

### Processing Flow

1. Document upload → File saved to `uploads/` directory
2. Background task extracts text and metadata
3. AI service analyzes document content
4. Results stored in database with structured data
5. Chat interface can reference analyzed documents

## Important Notes

- The [AI Provider] API integration requires a valid API key in environment variables
- Authentication is configured but not enforced (HTTPBearer setup in place)
- File uploads are limited to 50MB by default
- The system supports PDF, DOCX, and TXT file formats
- Database migrations should be run when models change