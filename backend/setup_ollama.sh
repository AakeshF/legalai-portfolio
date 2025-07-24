#!/bin/bash
# setup_ollama.sh - Script to install and configure Ollama for PrivateLegal AI

echo "🚀 PrivateLegal AI - Ollama Setup Script"
echo "========================================"
echo ""

# Detect OS
OS="Unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="Windows"
fi

echo "📍 Detected OS: $OS"
echo ""

# Function to check if Ollama is installed
check_ollama() {
    if command -v ollama &> /dev/null; then
        echo "✅ Ollama is already installed"
        return 0
    else
        echo "❌ Ollama is not installed"
        return 1
    fi
}

# Function to install Ollama
install_ollama() {
    echo "📦 Installing Ollama..."
    
    if [[ "$OS" == "macOS" ]]; then
        echo "Installing via Homebrew..."
        if ! command -v brew &> /dev/null; then
            echo "❌ Homebrew not found. Please install from https://brew.sh"
            exit 1
        fi
        brew install ollama
    elif [[ "$OS" == "Linux" ]]; then
        echo "Installing via official script..."
        curl -fsSL https://ollama.ai/install.sh | sh
    else
        echo "❌ Automatic installation not supported for $OS"
        echo "Please visit https://ollama.ai to download and install manually"
        exit 1
    fi
}

# Function to start Ollama service
start_ollama() {
    echo "🔄 Starting Ollama service..."
    
    if [[ "$OS" == "macOS" ]]; then
        # On macOS, Ollama runs as an app
        if pgrep -x "ollama" > /dev/null; then
            echo "✅ Ollama is already running"
        else
            echo "Starting Ollama..."
            ollama serve &
            sleep 5
        fi
    elif [[ "$OS" == "Linux" ]]; then
        # On Linux, it might be a systemd service
        if systemctl is-active --quiet ollama; then
            echo "✅ Ollama service is already running"
        else
            echo "Starting Ollama service..."
            sudo systemctl start ollama || ollama serve &
            sleep 5
        fi
    fi
}

# Function to pull recommended models
pull_models() {
    echo ""
    echo "📥 Pulling recommended models for legal AI..."
    echo ""
    
    # Pull Llama 3 8B (recommended for legal analysis)
    echo "1️⃣ Pulling Llama 3 8B (recommended)..."
    ollama pull llama3:8b
    
    echo ""
    echo "💡 Optional models for different use cases:"
    echo "   - mistral:7b (faster, good for quick analysis)"
    echo "   - llama3:70b (more accurate, requires 40GB+ RAM)"
    echo "   - codellama:13b (good for contract analysis)"
    echo ""
    echo "To pull additional models, run: ollama pull <model-name>"
}

# Function to test Ollama
test_ollama() {
    echo ""
    echo "🧪 Testing Ollama API..."
    
    # Test API endpoint
    if curl -s http://localhost:11434/api/tags > /dev/null; then
        echo "✅ Ollama API is responding"
        
        # List available models
        echo ""
        echo "📋 Available models:"
        ollama list
    else
        echo "❌ Ollama API is not responding"
        echo "Please ensure Ollama is running and try again"
        exit 1
    fi
}

# Function to update .env file
update_env() {
    echo ""
    echo "⚙️  Updating configuration..."
    
    if [ -f ".env" ]; then
        # Backup existing .env
        cp .env .env.backup
        echo "✅ Created backup: .env.backup"
    else
        # Create from example
        if [ -f ".env.example" ]; then
            cp .env.example .env
            echo "✅ Created .env from .env.example"
        else
            echo "❌ No .env.example found"
            return
        fi
    fi
    
    # Update AI provider settings
    sed -i.tmp 's/AI_PROVIDER=.*/AI_PROVIDER=ollama/' .env
    sed -i.tmp 's/OLLAMA_BASE_URL=.*/OLLAMA_BASE_URL=http:\/\/localhost:11434/' .env
    sed -i.tmp 's/OLLAMA_MODEL=.*/OLLAMA_MODEL=llama3:8b/' .env
    rm -f .env.tmp
    
    echo "✅ Updated .env with Ollama configuration"
}

# Main installation flow
echo "🔍 Checking Ollama installation..."
if ! check_ollama; then
    read -p "Would you like to install Ollama? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_ollama
    else
        echo "❌ Ollama is required for PrivateLegal AI"
        exit 1
    fi
fi

# Start Ollama
start_ollama

# Pull models
read -p "Would you like to pull the recommended AI models? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pull_models
fi

# Test installation
test_ollama

# Update configuration
read -p "Would you like to update your .env configuration? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    update_env
fi

echo ""
echo "✅ Ollama setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Ensure your .env file has the correct Ollama settings"
echo "2. Start the PrivateLegal AI backend: python start.py"
echo "3. The AI will use the local Ollama service for all operations"
echo ""
echo "🔒 Privacy Note: All AI processing happens locally on this machine."
echo "   No data is sent to external services."