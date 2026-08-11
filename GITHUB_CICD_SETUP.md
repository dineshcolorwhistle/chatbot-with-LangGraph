# GitHub CI/CD Setup & Deployment Guide for `aichat-staging`

This guide explains how the GitHub Actions CI/CD deployment pipeline works for the **LangGraph AI Chatbot** application and how to manage secrets and staging deployments.

---

## 1. Environment & Target Server Details

- **GitHub Deployment Environment**: `aichat-staging`
- **Target Server Remote Path**: `/home/agentwhistle-aichat-langgraph/htdocs/aichat-langgraph.agentwhistle.com/chatbot-with-LangGraph`
- **Backend Service Port**: `8020`
- **Workflow File**: [`.github/workflows/deploy-staging.yml`](file:///d:/Projects/chatbot-with-LangGraph/.github/workflows/deploy-staging.yml)

---

## 2. GitHub Secrets Configuration

Ensure the following secrets are added to your GitHub repository (**Settings** > **Secrets and variables** > **Actions** > **Environment secrets** for `aichat-staging` or **Repository secrets**):

| Secret Name | Description | Example / Value |
| :--- | :--- | :--- |
| `SSH_HOST` | Server IP or Domain Hostname | `aichat-langgraph.agentwhistle.com` or Server IP |
| `SSH_USER` | SSH Username on the server | `agentwhistle-aichat-langgraph` |
| `SSH_KEY` | Private SSH Key (PEM or OpenSSH format) | Content of private key `~/.ssh/id_rsa` or `~/.ssh/id_ed25519` |
| `SSH_PORT` | SSH Port (optional, default: `22`) | `22` |

### Adding Secrets in GitHub:
1. Go to your GitHub repository on GitHub.com.
2. Click **Settings** > **Secrets and variables** > **Actions**.
3. Under **Environment secrets**, select `aichat-staging` (or add as **Repository secrets**).
4. Click **New repository secret** (or **New environment secret**).
5. Add `SSH_HOST`, `SSH_USER`, `SSH_KEY`, and `SSH_PORT`.

---

## 3. Server Setup Requirements

Make sure the server `/home/agentwhistle-aichat-langgraph/htdocs/aichat-langgraph.agentwhistle.com/chatbot-with-LangGraph` meets the following criteria:

1. **Public Key Authorized**:
   The public key corresponding to `SSH_KEY` must be added to `/home/agentwhistle-aichat-langgraph/.ssh/authorized_keys` on the server:
   ```bash
   cat id_ed25519.pub >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```

2. **Git Repository Initialized**:
   Ensure the folder on the server is cloned from GitHub:
   ```bash
   cd /home/agentwhistle-aichat-langgraph/htdocs/aichat-langgraph.agentwhistle.com/chatbot-with-LangGraph
   git remote -v
   ```

3. **Backend `.env` File**:
   Ensure `backend/.env` exists on the server with production/staging credentials (`APP_PORT=8020`, MongoDB URI, Pinecone API Key, OpenAI/Ollama settings, SMTP credentials, JWT secret, etc.).

---

## 4. Triggering Deployments

The deployment runs automatically on:
- Any `push` to the `main` branch.
- Manual trigger from GitHub Actions tab using **Run workflow** (`workflow_dispatch`).

### Manual Trigger Instructions:
1. Go to GitHub > **Actions** tab.
2. Select **Deploy to Staging (aichat-staging)** workflow from the left sidebar.
3. Click **Run workflow**, select the branch (`main`), and click **Run workflow**.

---

## 5. Service Auto-Restart Detection

The deployment script automatically attempts to restart your FastAPI backend service using the following process managers if configured:
- **Systemd**: `systemctl restart aichat-backend`
- **PM2**: `pm2 restart aichat-backend`
- **Supervisor**: `supervisorctl restart aichat-backend`

If a custom service name or command is used, edit [`.github/workflows/deploy-staging.yml`](file:///d:/Projects/chatbot-with-LangGraph/.github/workflows/deploy-staging.yml) line 63-71 to match your server configuration.

---

## 6. Nginx Reverse Proxy Configuration (Port 8020)

Recommended Nginx server block for `aichat-langgraph.agentwhistle.com` routing to backend port `8020`:

```nginx
server {
  listen 80;
  listen [::]:80;
  listen 443 ssl;
  listen [::]:443 ssl;
  http2 on;
  
  server_name aichat-langgraph.agentwhistle.com;

  if ($scheme != "https") {
    rewrite ^ https://$host$request_uri permanent;
  }

  location ~ /.well-known {
    auth_basic off;
    allow all;
  }

  include /etc/nginx/global_settings;

  # Main proxy to FastAPI application on port 8020
  location / {
    proxy_pass http://127.0.0.1:8020;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_connect_timeout 900;
    proxy_send_timeout 900;
    proxy_read_timeout 900;
  }

  # Proxy static assets through FastAPI static directory mount
  location ~* ^.+\.(css|js|jpg|jpeg|gif|png|ico|gz|svg|svgz|ttf|otf|woff|woff2|eot|mp4|ogg|ogv|webm|webp|zip|swf)$ {
    proxy_pass http://127.0.0.1:8020;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    add_header Access-Control-Allow-Origin "*";
    expires 30d;
    access_log off;
  }

  if (-f $request_filename) {
    break;
  }
}
```
