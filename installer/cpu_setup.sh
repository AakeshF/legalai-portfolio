#!/bin/bash
# PrivateLegal AI - CPU-Only Setup for Dell T5810
# Temporary configuration while waiting for GPU

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}================================================${NC}"
echo -e "${YELLOW}   PrivateLegal AI - CPU Mode Setup${NC}"
echo -e "${YELLOW}================================================${NC}"
echo ""
echo -e "${RED}WARNING: CPU-only mode is for testing only!${NC}"
echo "Performance will be 10-50x slower than with GPU"
echo ""

# Install CPU-optimized builds
echo -e "${YELLOW}Installing CPU-optimized components...${NC}"

# Install llama.cpp for better CPU performance
if [ ! -d "/opt/llama.cpp" ]; then
    cd /opt
    git clone https://github.com/ggerganov/llama.cpp
    cd llama.cpp
    
    # Build with all CPU optimizations
    make clean
    make LLAMA_OPENBLAS=1 -j$(nproc)
fi

# Download smaller models for CPU
echo -e "${YELLOW}Downloading CPU-friendly models...${NC}"

# Phi-2 (2.7B) - Microsoft's small but capable model
if ! ollama list | grep -q "phi"; then
    ollama pull phi
fi

# TinyLlama (1.1B) - Fast on CPU
if ! ollama list | grep -q "tinyllama"; then
    ollama pull tinyllama
fi

# Orca Mini (3B) - Good balance
if ! ollama list | grep -q "orca-mini"; then
    ollama pull orca-mini
fi

# Configure for CPU usage
echo -e "${YELLOW}Optimizing for CPU...${NC}"

# Set thread count to physical cores (not hyperthreads)
PHYSICAL_CORES=$(lscpu | grep "Core(s) per socket" | awk '{print $4}')
SOCKETS=$(lscpu | grep "Socket(s)" | awk '{print $2}')
TOTAL_CORES=$((PHYSICAL_CORES * SOCKETS))

# Update Ollama environment
cat > /etc/systemd/system/ollama.service.d/cpu-override.conf << EOF
[Service]
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_NUM_THREAD=$TOTAL_CORES"
EOF

# Create CPU-specific config
cat > /opt/privatelegal/cpu_config.json << EOF
{
    "mode": "cpu_only",
    "recommended_models": {
        "fast": "tinyllama",
        "balanced": "phi",
        "quality": "orca-mini"
    },
    "settings": {
        "max_tokens": 512,
        "context_window": 2048,
        "threads": $TOTAL_CORES,
        "batch_size": 8
    },
    "warnings": [
        "Expect 30-60 second response times",
        "Limit document size to <10 pages",
        "Use for testing workflows only"
    ]
}
EOF

# Update application config for CPU mode
sed -i 's/OLLAMA_MODEL=.*/OLLAMA_MODEL=phi/' /opt/privatelegal/legal-ai/backend/.env

systemctl daemon-reload
systemctl restart ollama

echo ""
echo -e "${GREEN}CPU Mode Configuration Complete${NC}"
echo ""
echo "System specs detected:"
echo "- CPU Cores: $TOTAL_CORES physical cores"
echo "- RAM: $(free -h | awk '/^Mem:/{print $2}')"
echo ""
echo -e "${YELLOW}Performance Expectations:${NC}"
echo "- Simple queries: 30-60 seconds"
echo "- Document analysis: 2-5 minutes"
echo "- Multi-document search: Not recommended"
echo ""
echo -e "${RED}IMPORTANT:${NC}"
echo "1. This is temporary - order that GPU ASAP"
echo "2. Test workflows and UI, not performance"
echo "3. Keep documents under 10 pages"
echo ""
echo "Recommended test model: phi (2.7B parameters)"
echo "Run: ollama run phi"