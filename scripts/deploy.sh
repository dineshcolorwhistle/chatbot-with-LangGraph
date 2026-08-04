#!/bin/bash

set -e  # Exit immediately on error

echo "=========================================="
echo "🚀 Starting deployment for LangGraph AI Chatbot..."
echo "=========================================="

PROJECT_DIR="/home/agentwhistle-aichat-langgraph/htdocs/aichat-langgraph.agentwhistle.com/chatbot-with-LangGraph"
BACKEND_DIR="$PROJECT_DIR/backend"

cd "$PROJECT_DIR"

echo "➡️ Marking directory as safe for git..."
git config --global --add safe.directory "$PROJECT_DIR" || true
git config --global init.defaultBranch main || true

if [ ! -d ".git" ]; then
  echo "📦 Initializing new git repository..."
  git init -b main
fi

echo "🔄 Syncing git remote origin..."
git remote add origin https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git 2>/dev/null || git remote set-url origin https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git

echo "🔄 Fetching latest code..."
git fetch origin main
git reset --hard origin/main
git clean -fd

echo "⬇️ Latest code synced"

# -----------------------
# Backend Setup
# -----------------------
echo "⚙️ Backend setup..."
cd "$BACKEND_DIR"

if [ ! -d "venv" ]; then
  echo "📦 Creating Python virtual environment..."
  python3 -m venv venv
fi

source venv/bin/activate

echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Ensure backend/.env exists
if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    cp .env.example .env
    echo "⚠️ backend/.env was missing. Created from .env.example. Please update credentials!"
  fi
fi

# -----------------------
# Restart Backend Service
# -----------------------
echo "🔁 Restarting backend service..."

SERVICE_NAME=""
if systemctl is-active --quiet aichat 2>/dev/null; then
  SERVICE_NAME="aichat"
elif systemctl is-active --quiet aichat-backend 2>/dev/null; then
  SERVICE_NAME="aichat-backend"
elif systemctl is-active --quiet aichat-langgraph 2>/dev/null; then
  SERVICE_NAME="aichat-langgraph"
fi

if [ -n "$SERVICE_NAME" ]; then
  sudo systemctl restart "$SERVICE_NAME"
  sleep 2
  if ! systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "❌ Backend failed to restart ($SERVICE_NAME)"
    journalctl -u "$SERVICE_NAME" -n 50 --no-pager
    exit 1
  fi
  echo "✅ Service $SERVICE_NAME is running"
elif command -v pm2 >/dev/null 2>&1 && pm2 describe aichat-backend >/dev/null 2>&1; then
  pm2 restart aichat-backend
  echo "✅ Restarted via PM2"
elif command -v supervisorctl >/dev/null 2>&1 && supervisorctl status aichat-backend >/dev/null 2>&1; then
  sudo supervisorctl restart aichat-backend
  echo "✅ Restarted via Supervisor"
else
  echo "⚠️ Code updated. Please ensure your backend service process is restarted."
fi

echo "=========================================="
echo "🎉 Deployment completed successfully!"
echo "=========================================="
