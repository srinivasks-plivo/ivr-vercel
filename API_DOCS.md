# IVR System - API Documentation

**Base URL:** `https://your-project.vercel.app`

---

## General Endpoints

### `GET /`

Root info page. Returns list of all available endpoints.

**Response:**
```json
{
  "app": "IVR System on Vercel",
  "status": "running",
  "endpoints": { ... }
}
```

---

### `GET /api/health`

Health check. Tests connectivity to Redis and Postgres.

**Response (200 - healthy):**
```json
{
  "status": "healthy",
  "redis": "ok",
  "postgres": "ok",
  "timestamp": "2026-02-14T18:30:00.000000"
}
```

**Response (503 - unhealthy):**
```json
{
  "status": "unhealthy",
  "redis": "error: KV_REST_API_URL and KV_REST_API_TOKEN not set...",
  "postgres": "ok",
  "timestamp": "2026-02-14T18:30:00.000000"
}
```

---

### `POST /api/webhook-test`

Echo endpoint for testing webhooks. Accepts any POST data and returns it.

**Request:**
```bash
curl -X POST https://your-project.vercel.app/api/webhook-test \
  -H "Content-Type: application/json" \
  -d '{"test": "hello"}'
```

**Response (200):**
```json
{
  "received": true,
  "method": "POST",
  "content_type": "application/json",
  "data": { "test": "hello" },
  "timestamp": "2026-02-14T18:30:00.000000"
}
```

---

## Session Endpoints (Redis)

### `POST /api/start-session`

Create a new session in Redis with a 30-minute TTL.

**Query Parameters:**

| Param | Required | Description |
|-------|----------|-------------|
| `caller_id` | Yes | Phone number or unique ID (e.g., `+1234567890`) |

**Request:**
```bash
curl -X POST "https://your-project.vercel.app/api/start-session?caller_id=+1234567890"
```

**Response (200):**
```json
{
  "message": "Session created",
  "session": {
    "step": "greeting",
    "started_at": "2026-02-14T18:30:00.000000",
    "caller_id": "+1234567890"
  },
  "ttl_seconds": 1800
}
```

**Error (400):**
```json
{ "error": "caller_id query parameter required" }
```

---

### `GET /api/get-session`

Retrieve an existing session by caller ID.

**Query Parameters:**

| Param | Required | Description |
|-------|----------|-------------|
| `caller_id` | Yes | Phone number or unique ID |

**Request:**
```bash
curl "https://your-project.vercel.app/api/get-session?caller_id=+1234567890"
```

**Response (200):**
```json
{
  "session": {
    "step": "greeting",
    "started_at": "2026-02-14T18:30:00.000000",
    "caller_id": "+1234567890"
  }
}
```

**Error (404):**
```json
{ "error": "Session not found or expired" }
```

---

### `POST /api/update-session`

Update the step of an existing session.

**Query Parameters:**

| Param | Required | Description |
|-------|----------|-------------|
| `caller_id` | Yes | Phone number or unique ID |
| `step` | Yes | New step value (e.g., `menu_selection`, `transfer`) |

**Request:**
```bash
curl -X POST "https://your-project.vercel.app/api/update-session?caller_id=+1234567890&step=menu_selection"
```

**Response (200):**
```json
{
  "message": "Session updated",
  "session": {
    "step": "menu_selection",
    "started_at": "2026-02-14T18:30:00.000000",
    "caller_id": "+1234567890",
    "updated_at": "2026-02-14T18:31:00.000000"
  }
}
```

---

## Database Setup Endpoints

### `GET /api/setup-db`

Create all database tables. **Run once** after connecting Postgres via Vercel Storage.

**Request:**
```bash
curl https://your-project.vercel.app/api/setup-db
```

**Response (200):**
```json
{ "message": "Table created successfully" }
```

---

### `POST /api/seed-menus`

Seed the default IVR menu structure into Postgres. **Run once** after setup-db. Clears existing menus and creates fresh ones.

**Request:**
```bash
curl -X POST https://your-project.vercel.app/api/seed-menus
```

**Response (200):**
```json
{
  "message": "Seeded 4 menus successfully",
  "menus": [
    {
      "menu_id": "main_menu",
      "title": "Main Menu",
      "message": "Welcome. Press 1 for Sales, or Press 2 for Support.",
      "digit_actions": { "1": "sales_transfer", "2": "support_transfer" },
      "action_type": "menu",
      "is_active": true
    },
    {
      "menu_id": "sales_transfer",
      "title": "Sales Transfer",
      "message": "Connecting you to Sales. Please hold.",
      "action_type": "transfer",
      "is_active": true
    },
    {
      "menu_id": "support_transfer",
      "title": "Support Transfer",
      "message": "Connecting you to Support. Please hold.",
      "action_type": "transfer",
      "is_active": true
    },
    {
      "menu_id": "invalid_input",
      "title": "Invalid Input",
      "message": "Invalid input. Press 1 for Sales, or Press 2 for Support.",
      "digit_actions": { "1": "sales_transfer", "2": "support_transfer" },
      "action_type": "menu",
      "is_active": true
    }
  ]
}
```

---

## Call Log Endpoints (Postgres)

### `POST /api/log-call`

Insert a call record into the database.

**Request Body (JSON):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `call_uuid` | string | No | Unique call ID (auto-generated if omitted) |
| `from_number` | string | No | Caller's phone number |
| `to_number` | string | No | Destination phone number |
| `duration` | integer | No | Call duration in seconds |
| `call_status` | string | No | Status: `completed`, `abandoned`, `error` |
| `hangup_cause` | string | No | Reason call ended |
| `menu_path` | array | No | List of menu IDs visited |
| `user_inputs` | array | No | List of digit input records |

**Request:**
```bash
curl -X POST https://your-project.vercel.app/api/log-call \
  -H "Content-Type: application/json" \
  -d '{
    "from_number": "+1234567890",
    "to_number": "+0987654321",
    "duration": 120,
    "call_status": "completed",
    "menu_path": ["main_menu", "sales_transfer"],
    "user_inputs": [{"menu_id": "main_menu", "digit": "1"}]
  }'
```

**Response (201):**
```json
{
  "message": "Call logged",
  "call": {
    "id": 1,
    "call_uuid": "manual-1707940200.0",
    "from_number": "+1234567890",
    "to_number": "+0987654321",
    "start_time": "2026-02-14T18:30:00.000000",
    "end_time": null,
    "duration": 120,
    "call_status": "completed",
    "hangup_cause": "NORMAL_CLEARING",
    "menu_path": ["main_menu", "sales_transfer"],
    "user_inputs": [{"menu_id": "main_menu", "digit": "1"}],
    "created_at": "2026-02-14T18:30:00.000000"
  }
}
```

---

### `GET /api/call-logs`

Return all call logs, most recent first. Limited to 100 results.

**Request:**
```bash
curl https://your-project.vercel.app/api/call-logs
```

**Response (200):**
```json
{
  "count": 2,
  "logs": [
    {
      "id": 2,
      "call_uuid": "plivo-uuid-456",
      "from_number": "+1234567890",
      "duration": 45,
      "call_status": "completed",
      ...
    },
    {
      "id": 1,
      "call_uuid": "plivo-uuid-123",
      "from_number": "+1987654321",
      "duration": 120,
      "call_status": "completed",
      ...
    }
  ]
}
```

---

### `GET /api/call-history/:phone`

Return call logs for a specific phone number.

**URL Parameters:**

| Param | Description |
|-------|-------------|
| `phone` | Phone number (with or without `+` prefix) |

**Request:**
```bash
# With + prefix (URL-encoded as %2B)
curl "https://your-project.vercel.app/api/call-history/%2B1234567890"

# Without + prefix (auto-added)
curl https://your-project.vercel.app/api/call-history/1234567890
```

**Response (200):**
```json
{
  "phone": "+1234567890",
  "count": 3,
  "logs": [
    {
      "id": 5,
      "call_uuid": "plivo-uuid-789",
      "from_number": "+1234567890",
      "duration": 60,
      ...
    }
  ]
}
```

---

## Plivo Webhook Endpoints

These endpoints are called by Plivo during active phone calls. They accept `application/x-www-form-urlencoded` POST data and return Plivo XML.

### `POST /api/answer`

Called by Plivo when an incoming call arrives. Creates a Redis session and returns the main menu XML.

**Plivo sends:**

| Field | Description |
|-------|-------------|
| `CallUUID` | Unique call identifier |
| `From` | Caller's phone number |
| `To` | Your Plivo phone number |
| `CallStatus` | `ringing`, `answered`, etc. |

**Response (XML):**
```xml
<Response>
  <GetDigits action="https://your-project.vercel.app/api/handle-input" timeout="5" numDigits="1">
    <Speak>Welcome. Press 1 for Sales, or Press 2 for Support.</Speak>
  </GetDigits>
</Response>
```

**Plivo Configuration:**
- Set as Answer URL in Plivo Console → Phone Numbers → your number
- Method: POST

---

### `POST /api/handle-input`

Called by Plivo when the caller presses a digit. Validates input, determines next action, and returns appropriate XML.

**Plivo sends:**

| Field | Description |
|-------|-------------|
| `CallUUID` | Unique call identifier |
| `Digits` | Digit(s) the caller pressed |

**Response - Transfer (XML):**
```xml
<Response>
  <Speak>Connecting you to Sales. Please hold.</Speak>
  <Dial timeout="30">
    <Number>+1234567890</Number>
  </Dial>
</Response>
```

**Response - Invalid Input (XML):**
```xml
<Response>
  <Speak>Invalid input. Please try again.</Speak>
</Response>
```

---

### `POST /api/hangup`

Called by Plivo when the call ends. Saves call data to Postgres and cleans up the Redis session.

**Plivo sends:**

| Field | Description |
|-------|-------------|
| `CallUUID` | Unique call identifier |
| `HangupCause` | Why the call ended (e.g., `NORMAL_CLEARING`) |
| `Duration` | Call duration in seconds |
| `CallStatus` | Final status |

**Response:** Empty 200 OK

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "error": "Description of what went wrong"
}
```

| Status Code | Meaning |
|-------------|---------|
| 400 | Missing required parameters |
| 404 | Resource not found (session expired, no call logs) |
| 500 | Internal server error (check Vercel Logs) |
| 503 | Service unavailable (database or Redis down) |

---

## Testing with curl

```bash
BASE=https://your-project.vercel.app

# Health check
curl $BASE/api/health

# Create and manage sessions
curl -X POST "$BASE/api/start-session?caller_id=+1234567890"
curl "$BASE/api/get-session?caller_id=+1234567890"
curl -X POST "$BASE/api/update-session?caller_id=+1234567890&step=menu_selection"

# Database setup (run once)
curl $BASE/api/setup-db
curl -X POST $BASE/api/seed-menus

# Log a call
curl -X POST $BASE/api/log-call \
  -H "Content-Type: application/json" \
  -d '{"from_number":"+1234567890","to_number":"+0987654321","duration":60}'

# View logs
curl $BASE/api/call-logs
curl $BASE/api/call-history/1234567890
```
