# Chatwoot Agent Bot

A full-stack AI agent application — FastAPI backend + React (Vite) frontend — that provides a conversational interface for querying customer data via a LangGraph-powered agent.

---

## Prerequisites

Make sure the following are installed on your system **before** starting:

| Tool | Minimum Version | Download |
|------|----------------|---------|
| Python | 3.13+ | https://www.python.org/downloads/ |
| Node.js | 22+ | https://nodejs.org/ |
| Git | any | https://git-scm.com/ |
| PostgreSQL | latest (local) **or** Neon/Docker | see below |

---

## Project Structure

```
agent/
├── main.py              # FastAPI entry point
├── requirements.txt     # Python dependencies
├── .env                 # Backend environment variables  ← copy from .env.example
├── src/                 # Backend source code
└── web/                 # React frontend (Vite)
    ├── package.json
    └── .env.local       # Frontend environment variables ← copy from web/.env.local.example
```

---

## 1 · PostgreSQL Setup

Choose **one** of the options below.

### Option A — Neon (cloud, no local install needed)

1. Create a free project at [neon.tech](https://neon.tech)
2. Copy the connection string from the dashboard — it looks like:
   ```
   postgresql+asyncpg://user:password@ep-xxx.neon.tech/neondb?sslmode=require
   ```
3. Paste it as `DATABASE_URL` in your `.env` (step 3).

### Option B — Docker

```bash
docker run -d \
  --name postgres \
  -e POSTGRES_USER=myuser \
  -e POSTGRES_PASSWORD=mypassword \
  -e POSTGRES_DB=agentdb \
  -p 5432:5432 \
  postgres:15
```

Your `DATABASE_URL` will be:
```
postgresql+asyncpg://myuser:mypassword@localhost:5432/agentdb
```

### Option C — Local PostgreSQL install

Install PostgreSQL from https://www.postgresql.org/download/ and create a database:

```sql
CREATE DATABASE agentdb;
```

---

## 2 · Clone the Repository

```bash
git clone <your-repo-url>
cd agent
```

---

## 3 · Environment Variables

### Backend — `.env`

Copy the example file and fill in your values:

**Windows (PowerShell)**
```powershell
Copy-Item .env.example .env
```

**macOS / Linux**
```bash
cp .env.example .env
```

Then open `.env` and fill in:

```env
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...

CHATWOOT_BASE_URL=https://your-chatwoot-instance.com
CHATWOOT_ACCESS_TOKEN=your_access_token

# Local:   postgresql+asyncpg://username:password@localhost:5432/agentdb
# Neon:    postgresql+asyncpg://user:pass@ep-xxx.neon.tech/neondb?sslmode=require
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/database_name
```

### Frontend — `web/.env.local`

**Windows (PowerShell)**
```powershell
Copy-Item web\.env.local.example web\.env.local
```

**macOS / Linux**
```bash
cp web/.env.local.example web/.env.local
```

The default value points to your local backend — no changes needed for local dev:

```env
VITE_API_URL=http://localhost:8000
```

---

## 4 · Backend Setup

### Create & activate a virtual environment

**Windows (PowerShell)**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

> You should now see `(venv)` at the start of your terminal prompt.

### Install Python dependencies

```bash
pip install -r requirements.txt
```

### Start the backend dev server

```bash
fastapi dev main.py
```

The API will be available at **http://localhost:8000**  
Interactive docs (Swagger UI): **http://localhost:8000/docs**

---

## 5 · Frontend Setup

Open a **new terminal** (keep the backend running in the first one).

```bash
cd web
npm install
npm run dev
```

The frontend will be available at **http://localhost:5173**

---

## 6 · Quick-Start Cheat Sheet

```bash
# ── Terminal 1 · Backend ──────────────────────────────────────────
cd agent
python -m venv venv

# Windows:
.\venv\Scripts\Activate.ps1
# macOS / Linux:
# source venv/bin/activate

pip install -r requirements.txt
fastapi dev main.py

# ── Terminal 2 · Frontend ─────────────────────────────────────────
cd agent/web
npm install
npm run dev
```

---

## Available Scripts

### Backend

| Command | Description |
|---------|-------------|
| `fastapi dev main.py` | Start dev server with hot-reload |
| `uvicorn main:app --reload` | Alternative dev server start |

### Frontend (`web/` directory)

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite dev server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, LangGraph, SQLAlchemy (async), asyncpg |
| Frontend | React 19, Vite, TypeScript, TailwindCSS v4 |
| Database | PostgreSQL (local / Docker / Neon) |
| Auth | JWT (Bearer tokens) |
| AI | OpenAI, Tavily search |
