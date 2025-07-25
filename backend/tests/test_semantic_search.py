#!/usr/bin/env python3
"""Test semantic search functionality directly"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from services.semantic_search_sqlite import SQLiteSemanticSearchEngine
from services.document_processor import document_processor
from database import get_db
from models import Document, Organization
import uuid


async def test_semantic_search():
    """Test the semantic search engine"""

    # Create test organization
    db = next(get_db())

    # Check if test org exists
    org = db.query(Organization).filter_by(name="Test Organization").first()
    if not org:
        org = Organization(
            id=str(uuid.uuid4()),
            name="Test Organization",
            subscription_tier="professional",
            billing_email="[email@example.com]",
        )
        db.add(org)
        db.commit()

    print(f"📋 Using organization: {org.name} (ID: {org.id})")

    # Create a test document
    doc = Document(
        id=str(uuid.uuid4()),
        filename="test_contract.txt",
        file_path="/tmp/test_contract.txt",
        file_size=1000,
        extracted_content="This is a test contract with termination clauses. The contract can be terminated with 30 days notice. Early termination may result in penalties.",
        organization_id=org.id,
        processing_status="completed",
    )
    db.add(doc)
    db.commit()

    print(f"📄 Created test document: {doc.filename}")

    # Generate chunks and embeddings
    print("🔄 Generating chunks and embeddings...")
    await document_processor._generate_chunks_and_embeddings(
        db=db,
        document=doc,
        text=doc.extracted_content,
        metadata={"document_type": "contract"},
    )

    # Test semantic search
    print("\n🔍 Testing semantic search...")
    search_engine = SQLiteSemanticSearchEngine()

    # Test query
    query = "termination clauses"
    print(f"Query: '{query}'")

    results = await search_engine.search(query=query, organization_id=org.id, top_k=5)

    print(f"\n✅ Found {len(results)} results:")
    for i, result in enumerate(results):
        print(f"\n{i+1}. Document: {result.metadata.get('file_name', 'Unknown')}")
        print(f"   Score: {result.combined_score:.3f}")
        print(f"   Content: {result.content[:100]}...")

    db.close()


if __name__ == "__main__":
    asyncio.run(test_semantic_search())
