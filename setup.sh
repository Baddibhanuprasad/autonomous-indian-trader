#!/bin/bash

# Autonomous Indian Stock Trading Agent Setup Script

echo "🇮🇳 Setting up Autonomous Indian Stock Trading Agent"
echo "=================================================="

# Create virtual environment
echo "📦 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Setup directories
echo "📁 Creating directories..."
mkdir -p data logs config

# Copy configuration
echo "⚙️ Setting up configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Please edit .env file with your API credentials"
fi

if [ ! -f config/settings.yaml ]; then
    echo "Creating default settings.yaml..."
    cp config/settings.yaml.example config/settings.yaml 2>/dev/null || true
fi

# Initialize database
echo "🗄️ Initializing database..."
python -c "from src.data.database import DatabaseManager; DatabaseManager()"

# Pull Ollama model
echo "🤖 Pulling Ollama model (qwen2.5:7b)..."
if command -v ollama &> /dev/null; then
    ollama pull qwen2.5:7b
else
    echo "⚠️  Ollama not found. Please install it from https://ollama.ai"
fi

# Run tests
echo "🧪 Running tests..."
pytest tests/ -v

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 To start the system:"
echo "   1. Source the virtual environment: source venv/bin/activate"
echo "   2. Start with Docker: docker-compose up -d"
echo "   3. Or run directly: python -m src.main"
echo "   4. Dashboard: http://localhost:8501"
echo ""
echo "📝 Don't forget to:"
echo "   - Configure API credentials in .env"
echo "   - Add symbols to config/settings.yaml"
echo "   - Ensure Ollama is running with qwen2.5:7b model"