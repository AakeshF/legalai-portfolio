# Legal AI - On-Premise Legal Assistant

A secure, on-premise AI-powered legal document analysis and assistance system. This portfolio project demonstrates a complete implementation of an enterprise-grade legal AI system designed to run entirely on local infrastructure.

## Overview

Legal AI is a full-stack application that provides:
- Secure document processing and analysis
- AI-powered legal research assistance
- Multi-tenant organization support
- Complete data privacy with on-premise deployment
- Integration with local LLM models (Ollama)

## Technical Architecture

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with pgvector for semantic search
- **AI Integration**: Support for multiple AI providers (OpenAI, Anthropic, local models via Ollama)
- **Security**: JWT authentication, role-based access control, data encryption
- **Document Processing**: OCR, text extraction, semantic chunking

### Frontend
- **Framework**: React with TypeScript
- **UI Library**: Tailwind CSS
- **State Management**: Context API
- **Real-time Updates**: WebSocket integration
- **Performance**: Code splitting, lazy loading, service workers

## Key Features

- **Document Management**: Upload, process, and analyze legal documents
- **AI Chat Interface**: Context-aware legal assistance
- **Semantic Search**: Vector-based document search capabilities
- **Multi-tenancy**: Organization-based data isolation
- **Security First**: End-to-end encryption, audit logging
- **Offline Capable**: Works entirely on local infrastructure

## Installation

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Ollama (for local AI models)

### Quick Start

1. Clone the repository
```bash
git clone https://github.com/AakeshF/legalai-portfolio.git
cd legalai-portfolio
```

2. Install dependencies
```bash
cd backend && pip install -r requirements.txt
cd ../frontend && npm install
```

3. Run with Docker Compose
```bash
docker-compose up -d
```

4. Access the application at `http://localhost:3000`

## Architecture Highlights

- **Microservices**: Modular design with separate services for AI, documents, and auth
- **Caching**: Redis integration for performance optimization
- **Monitoring**: Prometheus metrics and structured logging
- **Scalability**: Horizontal scaling support with load balancing
- **Security**: OWASP compliance, security headers, rate limiting

## Technologies Used

- Python, FastAPI, SQLAlchemy
- React, TypeScript, Tailwind CSS
- PostgreSQL, pgvector, Redis
- Docker, Nginx
- Ollama, LangChain
- JWT, bcrypt

## Portfolio Notes

This project demonstrates:
- Full-stack development capabilities
- Enterprise security implementation
- AI/ML integration
- Modern DevOps practices
- Clean architecture principles
- Performance optimization techniques

## Contact

GitHub: [github.com/AakeshF](https://github.com/AakeshF)

---

*This is a portfolio project showcasing technical capabilities in building enterprise-grade AI applications.*