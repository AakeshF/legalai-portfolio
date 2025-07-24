#!/bin/bash
# PrivateLegal AI - CPU Performance Reality Check
# Shows what's actually possible without GPU

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}================================================${NC}"
echo -e "${YELLOW}   CPU-Only Performance Test${NC}"  
echo -e "${YELLOW}================================================${NC}"
echo ""

# Simple test prompt
TEST_PROMPT="What are the main obligations in this contract: The Buyer shall pay Seller \$50,000 within 30 days."

echo "Testing different models on CPU..."
echo "Prompt: \"$TEST_PROMPT\""
echo ""

# Test TinyLlama (1.1B) - Fastest
if ollama list | grep -q "tinyllama"; then
    echo -e "${GREEN}Testing TinyLlama (1.1B)...${NC}"
    start=$(date +%s)
    response=$(echo "$TEST_PROMPT" | timeout 120 ollama run tinyllama 2>/dev/null || echo "TIMEOUT")
    end=$(date +%s)
    duration=$((end - start))
    
    if [ "$response" != "TIMEOUT" ]; then
        echo "Response time: ${duration}s"
        echo "Usable: YES ✓"
    else
        echo "Response time: >120s (timeout)"
        echo "Usable: NO ✗"
    fi
    echo ""
fi

# Test Phi (2.7B) - Balanced
if ollama list | grep -q "phi"; then
    echo -e "${GREEN}Testing Phi-2 (2.7B)...${NC}"
    start=$(date +%s)
    response=$(echo "$TEST_PROMPT" | timeout 180 ollama run phi 2>/dev/null || echo "TIMEOUT")
    end=$(date +%s)
    duration=$((end - start))
    
    if [ "$response" != "TIMEOUT" ]; then
        echo "Response time: ${duration}s"
        if [ $duration -lt 60 ]; then
            echo "Usable: YES ✓"
        else
            echo "Usable: MARGINAL ⚠️"
        fi
    else
        echo "Response time: >180s (timeout)"
        echo "Usable: NO ✗"
    fi
    echo ""
fi

# DON'T even try Llama 3 8B on CPU
echo -e "${RED}Llama 3 8B on CPU:${NC}"
echo "Expected time: 5-10 minutes per response"
echo "Usable: NO ✗"
echo ""

# Recommendations
echo -e "${YELLOW}================================================${NC}"
echo -e "${YELLOW}   Recommendations for CPU-Only Testing${NC}"
echo -e "${YELLOW}================================================${NC}"
echo ""
echo "1. Use TinyLlama for UI/workflow testing only"
echo "2. Warn users: 'Demo mode - GPU arrives next week'"
echo "3. Test with single paragraph documents"
echo "4. Focus on:"
echo "   - Login/auth flow"
echo "   - Document upload UI"
echo "   - Navigation testing"
echo "   - Database operations"
echo ""
echo -e "${RED}What NOT to demo on CPU:${NC}"
echo "- Real document analysis"
echo "- Multi-document search"
echo "- Complex legal queries"
echo "- Performance benchmarks"
echo ""
echo "CPU mode is for testing the plumbing, not the water pressure."