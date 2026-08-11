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

# Use sudo only if not running as root; never prompt for password (-n flag)
if [ "$(id -u)" -eq 0 ]; then
  SUDO_CMD=""
else
  SUDO_CMD="sudo -n"
fi

if systemctl list-unit-files | grep -q "$SERVICE_NAME.service"; then
  if $SUDO_CMD systemctl restart "$SERVICE_NAME" 2>/dev/null; then
    sleep 2
    if systemctl is-active --quiet "$SERVICE_NAME"; then
      echo "✅ Service $SERVICE_NAME is running"
    else
      echo "❌ Backend failed to restart ($SERVICE_NAME)"
      $SUDO_CMD journalctl -u "$SERVICE_NAME" -n 50 --no-pager 2>/dev/null || true
      exit 1
    fi
  else
    echo "⚠️ Cannot restart $SERVICE_NAME — sudo requires a password."
    echo "⚠️ Fix: Run on server as root: echo 'agentwhistle-aichat-langgraph ALL=(ALL) NOPASSWD: /usr/bin/systemctl, /usr/bin/journalctl' > /etc/sudoers.d/aichat-deploy && chmod 0440 /etc/sudoers.d/aichat-deploy"
  fi
else
  echo "⚠️ Service '$SERVICE_NAME' not found. Please create /etc/systemd/system/$SERVICE_NAME.service on the server."
fi

echo "=========================================="
echo "🎉 Deployment completed successfully!"
echo "=========================================="
