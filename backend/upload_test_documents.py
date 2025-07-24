#!/usr/bin/env python3
"""
Upload test documents to the Legal AI system for RAG testing
"""

import requests
import json
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"

# Create test documents
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

This Agreement constitutes the entire understanding between the parties."""
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
from their negligence or breach."""
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
- Financial losses"""
    }
]

def upload_documents():
    """Upload test documents to the system"""
    
    # Create uploads directory if it doesn't exist
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    for doc in test_documents:
        print(f"\nUploading {doc['filename']}...")
        
        # Save to file
        file_path = upload_dir / doc['filename']
        with open(file_path, 'w') as f:
            f.write(doc['content'])
        
        # Upload via API
        with open(file_path, 'rb') as f:
            files = {'file': (doc['filename'], f, 'text/plain')}
            
            # Since auth is disabled for test endpoints, we'll use a simple upload
            response = requests.post(
                f"{BASE_URL}/api/documents/upload",
                files=files,
                headers={
                    "X-Organization-ID": "dev-org-id"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Uploaded successfully: {result.get('id')}")
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(f"   {response.text}")

def test_search():
    """Test semantic search after upload"""
    print("\n\nTesting semantic search...")
    
    queries = [
        "termination clauses",
        "confidentiality obligations", 
        "payment terms",
        "liability limitations",
        "intellectual property rights"
    ]
    
    for query in queries:
        print(f"\n🔍 Searching for: {query}")
        response = requests.post(
            f"{BASE_URL}/api/test/semantic-search",
            params={"query": query, "top_k": 3}
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"   Found {results['total']} results")
            for i, result in enumerate(results['results'][:3]):
                print(f"   {i+1}. Score: {result.get('relevance_score', 0):.3f}")
                print(f"      {result.get('content', '')[:100]}...")
        else:
            print(f"   ❌ Search failed: {response.text}")

def test_rag():
    """Test RAG chat after upload"""
    print("\n\nTesting RAG chat...")
    
    questions = [
        "What are the termination conditions in the employment agreement?",
        "What are the payment terms in the service agreement?",
        "What happens if someone breaches the NDA?",
        "What are the main risks mentioned in these contracts?"
    ]
    
    for question in questions:
        print(f"\n💬 Question: {question}")
        response = requests.post(
            f"{BASE_URL}/api/test/rag-chat",
            json={"message": question}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   Answer: {result.get('response', 'No response')[:200]}...")
            print(f"   Sources: {len(result.get('sources', []))}")
            print(f"   Confidence: {result.get('confidence', 0):.2f}")
        else:
            print(f"   ❌ RAG failed: {response.text}")

if __name__ == "__main__":
    print("📄 Legal AI Document Upload & Test Script")
    print("=" * 50)
    
    # First upload documents
    upload_documents()
    
    # Wait a bit for processing
    import time
    print("\n⏳ Waiting for document processing...")
    time.sleep(5)
    
    # Test search
    test_search()
    
    # Test RAG
    test_rag()
    
    print("\n✅ Testing complete!")