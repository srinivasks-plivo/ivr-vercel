# IVR System - Vercel Deployment

A production-ready Interactive Voice Response (IVR) system deployed on Vercel serverless functions. Built with Flask, Plivo Voice API, Upstash Redis, and Neon Postgres.

## Architecture

```
Caller's Phone
      │
      ▼
Plivo Voice Network
      │
      ▼ HTTP POST webhooks
┌─────────────────────────────┐
│   Vercel Serverless (Flask) │
│                             │
│  /api/answer                │
│  /api/handle-input          │
│  /api/hangup                │
└──────┬──────────┬───────────┘
       │          │
       ▼          ▼
   Upstash     Neon
   Redis       Postgres
  (sessions)  (call logs)
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Runtime | Vercel Serverless Functions | Hosts the Flask app |
| Framework | Flask 3.0+ | HTTP routing and request handling |
| Voice API | Plivo | Handles phone calls via XML webhooks |
| Sessions | Upstash Redis (REST API) | Temporary call session storage with TTL |
| Database | Neon Postgres (via SQLAlchemy) | Permanent call logs and menu config |

## Project Structure

```
ivr-vercel/
├── api/
│   └── index.py              # Flask app with all API endpoints
├── models/
│   ├── __init__.py
│   ├── database.py           # SQLAlchemy engine (NullPool for serverless)
│   ├── call_log.py           # CallLog table model
│   ├── caller_history.py     # CallerHistory table model
│   └── menu_config.py        # MenuConfiguration table model
├── services/
│   ├── __init__.py
│   ├── ivr_service.py        # IVR call flow orchestrator
│   ├── plivo_service.py      # Plivo XML response generator
│   └── redis_service.py      # Upstash Redis session manager
├── scripts/
│   └── test_endpoints.py     # Endpoint test script
├── config.py                 # Environment variable configuration
├── vercel.json               # Vercel build and routing config
├── requirements.txt          # Python dependencies
└── .env.example              # Environment variable reference
```

## Setup

### Prerequisites

- [Vercel account](https://vercel.com) with GitHub connected
- [Plivo account](https://console.plivo.com) with a phone number
- [Vercel CLI](https://vercel.com/docs/cli) installed: `npm install -g vercel`

### 1. Deploy to Vercel

```bash
cd ivr-vercel
vercel
```

Follow the prompts to link to your Vercel account.

### 2. Add Storage (Vercel Dashboard)

**Redis:**
- Project → Storage tab → Create Database → Redis (Upstash)
- Name: `ivr-sessions` → Create → Connect to Project

**Postgres:**
- Project → Storage tab → Create Database → Postgres (Neon)
- Name: `ivr-call-logs` → Create → Connect to Project

Vercel auto-configures these environment variables:

| Variable | Source |
|----------|--------|
| `KV_REST_API_URL` | Redis (Upstash) |
| `KV_REST_API_TOKEN` | Redis (Upstash) |
| `POSTGRES_URL` | Postgres (Neon) |

### 3. Add Environment Variables (Vercel Dashboard)

Go to Settings → Environment Variables and add:

| Variable | Value |
|----------|-------|
| `PLIVO_AUTH_ID` | Your Plivo Auth ID |
| `PLIVO_AUTH_TOKEN` | Your Plivo Auth Token |
| `PLIVO_PHONE_NUMBER` | Your Plivo phone number |
| `SALES_TRANSFER_NUMBER` | Sales department number |
| `SUPPORT_TRANSFER_NUMBER` | Support department number |
| `WEBHOOK_BASE_URL` | `https://your-project.vercel.app` |

### 4. Redeploy and Initialize

```bash
vercel --prod
```

Then initialize the database and seed menus:

```bash
# Create tables
curl https://your-project.vercel.app/api/setup-db

# Seed IVR menus
curl -X POST https://your-project.vercel.app/api/seed-menus
```

### 5. Configure Plivo

- Plivo Console → Phone Numbers → click your number
- Answer URL: `https://your-project.vercel.app/api/answer` (POST)
- Save

### 6. Test

```bash
python scripts/test_endpoints.py https://your-project.vercel.app
```

Or call your Plivo number and follow the menu prompts.

## IVR Call Flow

```
1. Caller dials your Plivo number
2. Plivo POSTs to /api/answer
3. App creates Redis session, loads main menu from Postgres
4. Returns XML: "Welcome. Press 1 for Sales, Press 2 for Support."
5. Caller presses a digit
6. Plivo POSTs digit to /api/handle-input
7. App validates digit, determines next action
8. Returns XML: transfer call, show submenu, or hang up
9. Call ends → Plivo POSTs to /api/hangup
10. App saves call log to Postgres, deletes Redis session
```

## Environment Variables Reference

See [.env.example](.env.example) for all variables. Storage variables (`KV_*`, `POSTGRES_*`) are auto-configured by Vercel when you connect databases via the Storage tab.

## Monitoring

- **Health check:** `GET /api/health` — checks Redis and Postgres connectivity
- **Vercel Logs:** Dashboard → Deployments → click deployment → Logs
- **Redis Data:** Dashboard → Storage → Redis → Data Browser
- **Postgres Data:** Dashboard → Storage → Postgres → Data tab
