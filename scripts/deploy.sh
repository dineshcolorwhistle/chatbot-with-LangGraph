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
SERVICE_NAME="aichat-backend"
echo "🔁 Restarting backend service ($SERVICE_NAME)..."

SUDO_CMD=""
if [ "$(id -u)" -ne 0 ]; then
  SUDO_CMD="sudo -n"
fi

if systemctl list-unit-files | grep -q "$SERVICE_NAME.service"; then
  $SUDO_CMD systemctl restart "$SERVICE_NAME" 2>/dev/null || systemctl restart "$SERVICE_NAME" 2>/dev/null || sudo systemctl restart "$SERVICE_NAME"
  sleep 2
  if ! systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "❌ Backend failed to restart ($SERVICE_NAME)"
    $SUDO_CMD journalctl -u "$SERVICE_NAME" -n 50 --no-pager 2>/dev/null || journalctl -u "$SERVICE_NAME" -n 50 --no-pager
    exit 1
  fi
  echo "✅ Service $SERVICE_NAME is running"
elif command -v pm2 >/dev/null 2>&1 && pm2 describe "$SERVICE_NAME" >/dev/null 2>&1; then
  pm2 restart "$SERVICE_NAME"
  echo "✅ Restarted via PM2 ($SERVICE_NAME)"
elif command -v supervisorctl >/dev/null 2>&1 && supervisorctl status "$SERVICE_NAME" >/dev/null 2>&1; then
  $SUDO_CMD supervisorctl restart "$SERVICE_NAME" 2>/dev/null || supervisorctl restart "$SERVICE_NAME"
  echo "✅ Restarted via Supervisor ($SERVICE_NAME)"
else
  echo "⚠️ Code updated. Please ensure systemd service '$SERVICE_NAME' is created and running."
fi

echo "=========================================="
echo "🎉 Deployment completed successfully!"
echo "=========================================="
