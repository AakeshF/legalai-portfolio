#!/bin/bash
# PrivateLegal AI - Hardware Performance Test
# Tests Ollama performance on specific hardware configurations

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}   PrivateLegal AI - Hardware Performance Test${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}Ollama is not installed!${NC}"
    echo "Please run: curl -fsSL https://ollama.ai/install.sh | sh"
    exit 1
fi

# Check NVIDIA GPU
echo -e "${YELLOW}Checking GPU...${NC}"
if ! nvidia-smi &> /dev/null; then
    echo -e "${RED}NVIDIA GPU not detected!${NC}"
    exit 1
fi

# Display GPU info
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
echo ""

# Test document content
TEST_DOCUMENT="This is a test legal document for performance benchmarking. 

PURCHASE AGREEMENT

This Purchase Agreement (this 'Agreement') is entered into as of January 15, 2024 (the 'Effective Date'), by and between Tech Innovations LLC, a Delaware limited liability company ('Buyer'), and Digital Assets Inc., a California corporation ('Seller').

WHEREAS, Seller desires to sell, and Buyer desires to purchase, certain assets of Seller's business related to artificial intelligence software development;

NOW, THEREFORE, in consideration of the mutual covenants and agreements set forth herein, and for other good and valuable consideration, the receipt and sufficiency of which are hereby acknowledged, the parties agree as follows:

1. PURCHASE AND SALE OF ASSETS
   1.1 Assets. Subject to the terms and conditions of this Agreement, Seller agrees to sell, convey, transfer, assign and deliver to Buyer, and Buyer agrees to purchase and acquire from Seller, all of Seller's right, title and interest in and to the following assets (collectively, the 'Assets'):
   
   (a) All intellectual property rights, including but not limited to patents, trademarks, copyrights, and trade secrets related to the AI Software;
   (b) All source code, object code, documentation, and related materials;
   (c) All customer contracts and relationships;
   (d) All equipment and hardware specifically used for the AI Software development.

2. PURCHASE PRICE
   2.1 The aggregate purchase price for the Assets shall be Ten Million Dollars ($10,000,000) (the 'Purchase Price').
   2.2 Payment Terms. The Purchase Price shall be paid as follows:
       (a) Five Million Dollars ($5,000,000) in cash at Closing;
       (b) Five Million Dollars ($5,000,000) in a promissory note with 5% annual interest, payable over 3 years.

3. REPRESENTATIONS AND WARRANTIES
   3.1 Seller represents and warrants that:
       (a) Seller has full corporate power and authority to enter into this Agreement;
       (b) The execution and delivery of this Agreement has been duly authorized;
       (c) Seller has good and marketable title to the Assets, free and clear of all liens;
       (d) There is no pending or threatened litigation relating to the Assets.

4. INDEMNIFICATION
   4.1 Seller shall indemnify, defend, and hold harmless Buyer from and against any and all losses, damages, liabilities, costs, and expenses arising out of any breach of Seller's representations or warranties.

5. CONFIDENTIALITY
   5.1 Each party agrees to maintain the confidentiality of all non-public information received from the other party.

6. GOVERNING LAW
   This Agreement shall be governed by the laws of the State of Delaware, without regard to its conflict of laws principles.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above."

# Function to test a model
test_model() {
    local model=$1
    local model_size=$2
    
    echo -e "${BLUE}Testing $model (Size: $model_size)...${NC}"
    
    # Pull model if not exists
    if ! ollama list | grep -q "$model"; then
        echo "Pulling $model..."
        ollama pull "$model"
    fi
    
    # Prepare test prompt
    local prompt="Analyze this legal document and extract: 1) All parties involved, 2) Key dates, 3) Monetary amounts, 4) Main obligations. Document: $TEST_DOCUMENT"
    
    # Run inference test with timing
    echo "Running inference test..."
    local start_time=$(date +%s.%N)
    
    # Run the model
    local response=$(echo "$prompt" | ollama run "$model" --verbose 2>&1)
    
    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)
    
    # Extract performance metrics from verbose output
    local tokens_per_sec=$(echo "$response" | grep -oP 'eval \K[0-9.]+(?= tokens/s)' | head -1)
    local total_tokens=$(echo "$response" | grep -oP 'eval count: \K[0-9]+' | head -1)
    
    # Memory usage
    local gpu_mem=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
    
    # Display results
    echo -e "  ${GREEN}✓${NC} Inference time: ${duration}s"
    echo -e "  ${GREEN}✓${NC} Tokens/second: ${tokens_per_sec:-N/A}"
    echo -e "  ${GREEN}✓${NC} Total tokens: ${total_tokens:-N/A}"
    echo -e "  ${GREEN}✓${NC} GPU memory used: ${gpu_mem}MB"
    echo ""
    
    # Test result quality (basic check)
    if echo "$response" | grep -q "Tech Innovations LLC\|Digital Assets Inc"; then
        echo -e "  ${GREEN}✓${NC} Quality check: Model correctly identified parties"
    else
        echo -e "  ${YELLOW}⚠${NC} Quality check: Model may have missed key information"
    fi
    
    echo ""
    
    # Return performance score (tokens/sec)
    echo "$tokens_per_sec"
}

# System info
echo -e "${YELLOW}System Information:${NC}"
echo "CPU: $(lscpu | grep 'Model name' | cut -d ':' -f2 | xargs)"
echo "RAM: $(free -h | awk '/^Mem:/{print $2}')"
echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader)"
echo "GPU Memory: $(nvidia-smi --query-gpu=memory.total --format=csv,noheader)"
echo ""

# Test models suitable for RTX 3090 (24GB VRAM)
echo -e "${YELLOW}Starting performance tests...${NC}"
echo ""

# Test Llama 3 8B (recommended)
perf_llama3_8b=$(test_model "llama3:8b" "8B parameters")

# Test Mistral 7B (faster alternative)
perf_mistral=$(test_model "mistral:7b" "7B parameters")

# Test Llama 2 13B (if memory allows)
if [ $(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1) -gt 15000 ]; then
    perf_llama2_13b=$(test_model "llama2:13b" "13B parameters")
else
    echo -e "${YELLOW}Skipping Llama 2 13B - insufficient GPU memory${NC}"
    perf_llama2_13b=0
fi

# Summary
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}   Performance Test Summary${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

# Determine best model
best_model="llama3:8b"
best_perf=$perf_llama3_8b

if [ "$(echo "$perf_mistral > $best_perf" | bc -l)" -eq 1 ] 2>/dev/null; then
    best_model="mistral:7b"
    best_perf=$perf_mistral
fi

echo -e "Recommended model for your hardware: ${GREEN}$best_model${NC}"
echo ""
echo "Performance expectations:"
echo "- Document analysis: 5-15 seconds"
echo "- Contract review: 10-30 seconds"
echo "- Multi-document search: 20-60 seconds"
echo ""

# Check if performance is acceptable
if [ "$(echo "$best_perf > 30" | bc -l)" -eq 1 ] 2>/dev/null; then
    echo -e "${GREEN}✓ Your hardware exceeds minimum requirements!${NC}"
    echo "  Expected performance: Excellent"
elif [ "$(echo "$best_perf > 20" | bc -l)" -eq 1 ] 2>/dev/null; then
    echo -e "${GREEN}✓ Your hardware meets recommended requirements!${NC}"
    echo "  Expected performance: Good"
elif [ "$(echo "$best_perf > 10" | bc -l)" -eq 1 ] 2>/dev/null; then
    echo -e "${YELLOW}⚠ Your hardware meets minimum requirements${NC}"
    echo "  Expected performance: Acceptable"
    echo "  Consider upgrading to RTX 4090 for better performance"
else
    echo -e "${RED}✗ Performance may be below acceptable levels${NC}"
    echo "  Consider using smaller models or upgrading hardware"
fi

# Save configuration recommendation
cat > hardware_config.json << EOF
{
    "tested_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "gpu": "$(nvidia-smi --query-gpu=name --format=csv,noheader)",
    "gpu_memory": "$(nvidia-smi --query-gpu=memory.total --format=csv,noheader)",
    "recommended_model": "$best_model",
    "performance_score": "$best_perf",
    "models_tested": {
        "llama3:8b": "$perf_llama3_8b",
        "mistral:7b": "$perf_mistral",
        "llama2:13b": "$perf_llama2_13b"
    }
}
EOF

echo ""
echo "Configuration saved to: hardware_config.json"
echo ""
echo -e "${GREEN}Test complete!${NC}"