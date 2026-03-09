#!/bin/bash
# NyaySetu — GitHub Codespaces Auto Setup
# This runs automatically when the Codespace starts

set -e  # exit on error
echo ""
echo "=================================================="
echo "  ⚖️  NyaySetu — Setting up your environment"
echo "=================================================="
echo ""

# ── 1. Install Ollama ─────────────────────────────────────────────────────────
echo "📦 Step 1/5: Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh
echo "✅ Ollama installed"

# ── 2. Start Ollama in background ────────────────────────────────────────────
echo ""
echo "🚀 Step 2/5: Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!
sleep 5  # wait for server to be ready
echo "✅ Ollama running (PID: $OLLAMA_PID)"

# ── 3. Pull LLM model ────────────────────────────────────────────────────────
echo ""
echo "🤖 Step 3/5: Downloading LLM model (llama3.2 ~2GB)..."
echo "   This takes 2-5 minutes on first setup. Coffee time ☕"
ollama pull llama3.2
echo "✅ Model ready"

# ── 4. Install Python backend deps ───────────────────────────────────────────
echo ""
echo "🐍 Step 4/5: Installing Python dependencies..."
cd /workspaces/nyaysetu/backend
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✅ Python packages installed"

# ── 5. Install Node frontend deps ────────────────────────────────────────────
echo ""
echo "⚛️  Step 5/5: Installing frontend dependencies..."
cd /workspaces/nyaysetu/frontend
npm install --silent
echo "✅ Node packages installed"

# ── 6. Copy env file ─────────────────────────────────────────────────────────
cd /workspaces/nyaysetu/backend
if [ ! -f .env ]; then
  cp .env.example .env
  echo "✅ .env created from template"
fi

# ── 7. Seed the law database ─────────────────────────────────────────────────
echo ""
echo "📚 Seeding Indian law database (first-time scrape)..."
echo "   Scraping India Code, eGazette, Supreme Court, RBI..."
echo "   This runs in background — takes 5-10 minutes"
cd /workspaces/nyaysetu/backend
python -m pipeline.scheduler &
echo "✅ Database seeding started in background"

echo ""
echo "=================================================="
echo "  🎉 Setup complete! Run the app:"
echo ""
echo "  Terminal 1 (Backend):"
echo "    cd backend && uvicorn main:app --reload --port 8000"
echo ""
echo "  Terminal 2 (Frontend):"
echo "    cd frontend && npm run dev"
echo ""
echo "  Then open port 5173 in your browser."
echo "=================================================="
echo ""
