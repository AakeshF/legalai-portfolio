#!/bin/bash
# Script to run backend tests with coverage

echo "🧪 Running Backend Tests with Coverage"
echo "======================================"

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Virtual environment not activated. Activating..."
    source venv/bin/activate 2>/dev/null || {
        echo "❌ Failed to activate virtual environment"
        echo "   Please run: python -m venv venv && source venv/bin/activate"
        exit 1
    }
fi

# Install test requirements if needed
echo "📦 Installing test requirements..."
pip install -q -r requirements-test.txt

# Clean up any existing test database
rm -f test_legal_ai.db test_legal_ai.db-journal

# Set test environment variables
export ENVIRONMENT=testing
export DATABASE_URL=sqlite:///./test_legal_ai.db
export DISABLE_AUTH=False
export JWT_SECRET_KEY=test-secret-key-for-testing-only
export SECRET_KEY=test-secret-key-for-testing-only
export ENCRYPTION_KEY=test-encryption-key-for-testing
export DEEPSEEK_API_KEY=test-api-key

# Run tests with coverage
echo ""
echo "🏃 Running tests..."
echo ""

# Run specific test suites
if [ "$1" == "auth" ]; then
    pytest tests/test_auth.py -v --cov=auth --cov=auth_routes --cov=auth_middleware --cov=auth_utils
elif [ "$1" == "documents" ]; then
    pytest tests/test_documents.py -v --cov=services.document_processor --cov=main
elif [ "$1" == "chat" ]; then
    pytest tests/test_chat.py -v --cov=services.ai_service --cov=main
elif [ "$1" == "ai" ]; then
    pytest tests/test_ai_service.py -v --cov=services.ai_service --cov=services.hybrid_ai_service
elif [ "$1" == "quick" ]; then
    # Quick test run without coverage
    pytest -v -m "not slow"
else
    # Run all tests with full coverage
    pytest -v
fi

# Check if tests passed
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    echo ""
    echo "📊 Coverage report generated in htmlcov/index.html"
    echo "   Open with: open htmlcov/index.html"
else
    echo ""
    echo "❌ Tests failed!"
    exit 1
fi

# Clean up
rm -f test_legal_ai.db test_legal_ai.db-journal

echo ""
echo "🧹 Cleanup complete"