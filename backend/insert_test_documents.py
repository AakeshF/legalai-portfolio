#!/usr/bin/env python3
"""
Directly insert test documents into the database for RAG testing
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Document, DocumentChunk, ChunkEmbedding, EmbeddingModel
from services.document_chunker import LegalDocumentChunker
from services.embedding_service import EmbeddingService
from config import settings

# Test documents
test_documents = [
    {
        "filename": "employment_contract.txt",
        "content": """EMPLOYMENT AGREEMENT

This Employment Agreement ("Agreement") is entered into as of January 1, 2024, 
between TechCorp Inc. ("Company") and John Doe ("Employee").

1. POSITION AND DUTIES
Employee shall serve as Senior Software Engineer and perform duties as assigned 
by the Company.

2. COMPENSATION
Employee shall receive an annual salary of $120,000, payable in accordance with 
Company's standard payroll practices.

3. TERMINATION
Either party may terminate this Agreement with 30 days written notice. The Company 
may terminate immediately for cause, including but not limited to:
- Material breach of company policies
- Misconduct or negligence
- Disclosure of confidential information

4. CONFIDENTIALITY
Employee agrees to maintain strict confidentiality of all proprietary information 
and trade secrets during and after employment.

5. NON-COMPETE
For 12 months following termination, Employee shall not engage in any business 
that directly competes with Company within a 50-mile radius.

6. SEVERANCE
In case of termination without cause, Employee shall receive 3 months severance pay.

7. DISPUTE RESOLUTION
Any disputes shall be resolved through binding arbitration in accordance with 
state law.

This Agreement constitutes the entire understanding between the parties.""",
    },
    {
        "filename": "service_agreement.txt",
        "content": """SERVICE AGREEMENT

This Service Agreement ("Agreement") is made between ClientCo LLC ("Client") 
and ServicePro Inc. ("Service Provider").

1. SERVICES
Service Provider agrees to provide IT consulting services including:
- System architecture design
- Security assessment
- Performance optimization
- 24/7 technical support

2. PAYMENT TERMS
Client shall pay $10,000 monthly, due within 30 days of invoice.
Late payments incur 1.5% monthly interest.

3. SERVICE LEVELS
- 99.9% uptime guarantee
- 4-hour response time for critical issues
- Monthly performance reports

4. LIABILITY
Service Provider's liability is limited to the fees paid in the last 12 months.
Neither party liable for indirect or consequential damages.

5. TERMINATION CLAUSES
- Either party may terminate with 60 days notice
- Immediate termination for material breach
- Client must pay for all services rendered

6. INTELLECTUAL PROPERTY
All work product created under this Agreement belongs to Client.
Service Provider retains rights to general methodologies.

7. WARRANTIES
Service Provider warrants services will be performed professionally and 
in accordance with industry standards.

8. INDEMNIFICATION
Each party shall indemnify the other against third-party claims arising 
from their negligence or breach.""",
    },
    {
        "filename": "nda_agreement.txt",
        "content": """NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement ("Agreement") is entered into between 
Disclosing Party and Receiving Party.

1. CONFIDENTIAL INFORMATION
"Confidential Information" means all non-public information disclosed by 
either party, including:
- Business strategies and plans
- Financial information
- Customer lists and data
- Technical specifications
- Trade secrets

2. OBLIGATIONS
Receiving Party agrees to:
- Maintain strict confidentiality
- Use information only for evaluation purposes
- Not disclose to third parties without written consent
- Return all materials upon request

3. EXCEPTIONS
Obligations do not apply to information that:
- Is publicly available
- Was known prior to disclosure
- Is independently developed
- Must be disclosed by law

4. TERM
This Agreement remains in effect for 5 years from the date of signing.
Confidentiality obligations survive termination.

5. BREACH AND REMEDIES
Breach may cause irreparable harm. Disclosing Party entitled to:
- Injunctive relief
- Monetary damages
- Attorney's fees

6. GOVERNING LAW
This Agreement is governed by the laws of the state where executed.

7. RISKS
Unauthorized disclosure may result in:
- Loss of competitive advantage
- Legal liability
- Damage to business relationships
- Financial losses""",
    },
]


async def main():
    print("📄 Inserting test documents into Legal AI database")
    print("=" * 50)

    # Create database connection
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    # Initialize services
    chunker = LegalDocumentChunker()
    embedding_service = EmbeddingService()

    # Get or create embedding model
    model_name = embedding_service.model_name
    embedding_model = (
        db.query(EmbeddingModel).filter(EmbeddingModel.name == model_name).first()
    )

    if not embedding_model:
        embedding_model = EmbeddingModel(
            id=str(uuid4()),
            name=model_name,
            provider=embedding_service.provider,
            dimension=384,  # all-mpnet-base-v2 dimension
            created_at=datetime.utcnow(),
        )
        db.add(embedding_model)
        db.commit()
        print(f"✅ Created embedding model: {model_name}")

    try:
        for doc_data in test_documents:
            print(f"\n📝 Processing {doc_data['filename']}...")

            # Create document record
            doc_id = str(uuid4())
            file_path = f"uploads/{doc_data['filename']}"

            # Create uploads directory if needed
            os.makedirs("uploads", exist_ok=True)

            # Save file
            with open(file_path, "w") as f:
                f.write(doc_data["content"])

            document = Document(
                id=doc_id,
                filename=doc_data["filename"],
                file_path=file_path,
                file_size=len(doc_data["content"]),
                content_type="text/plain",
                organization_id="dev-org-id",
                uploaded_by_id="test-user",
                processing_status="completed",
                upload_timestamp=datetime.utcnow(),
                processed_timestamp=datetime.utcnow(),
                extracted_content=doc_data["content"],
                summary=f"Legal document: {doc_data['filename']}",
                page_count=1,
                legal_metadata=json.dumps(
                    {
                        "document_type": "contract",
                        "jurisdiction": "US",
                        "parties": ["Party A", "Party B"],
                    }
                ),
            )

            db.add(document)
            db.commit()
            print(f"   ✅ Document saved: {doc_id}")

            # Create chunks
            chunk_objects = chunker.chunk_document(
                text=doc_data["content"],
                document_type="contract",
                metadata={"filename": doc_data["filename"]},
            )
            print(f"   📄 Created {len(chunk_objects)} chunks")

            # Store chunks and generate embeddings
            for i, chunk_obj in enumerate(chunk_objects):
                print(f"   🔍 Processing chunk {i+1}/{len(chunk_objects)}...", end="\r")

                # Create chunk in database
                chunk_id = str(uuid4())
                db_chunk = DocumentChunk(
                    id=chunk_id,
                    document_id=doc_id,
                    content=chunk_obj.content,
                    chunk_index=chunk_obj.chunk_index,
                    tokens=chunk_obj.tokens,
                    start_char=chunk_obj.start_char,
                    end_char=chunk_obj.end_char,
                    chunk_metadata=chunk_obj.metadata,
                )
                db.add(db_chunk)

                # Generate and store embedding
                embedding_result = await embedding_service.generate_embedding(
                    chunk_obj.content
                )

                # Store embedding in database
                embedding_record = ChunkEmbedding(
                    chunk_id=chunk_id,
                    model_id=embedding_model.id,
                    embedding=json.dumps(embedding_result.embedding),
                    created_at=datetime.utcnow(),
                )
                db.add(embedding_record)

            db.commit()
            print(f"\n   ✅ All chunks processed and embedded")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        db.rollback()
    finally:
        db.close()

    print("\n✅ Document insertion complete!")
    print("\nYou can now test:")
    print("1. Semantic search: /api/test/semantic-search")
    print("2. RAG chat: /api/test/rag-chat")


if __name__ == "__main__":
    asyncio.run(main())
