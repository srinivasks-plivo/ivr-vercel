"""
Test script for Vercel-deployed IVR endpoints.

Usage:
    python scripts/test_endpoints.py https://your-project.vercel.app
"""

import sys
import json
import urllib.request
import urllib.parse
import urllib.error


def make_request(url, method="GET", data=None, content_type=None):
    """Make HTTP request and return response."""
    if data and isinstance(data, dict):
        if content_type == "application/json":
            data = json.dumps(data).encode('utf-8')
        else:
            data = urllib.parse.urlencode(data).encode('utf-8')

    req = urllib.request.Request(url, data=data, method=method)
    if content_type:
        req.add_header('Content-Type', content_type)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode('utf-8')
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        return e.code, body
    except Exception as e:
        return 0, str(e)


def test_all(base_url):
    base_url = base_url.rstrip('/')
    passed = 0
    failed = 0

    def check(name, status, body, expected_status=200):
        nonlocal passed, failed
        ok = status == expected_status
        icon = "PASS" if ok else "FAIL"
        print(f"  [{icon}] {name} -> {status}")
        if not ok:
            print(f"         Expected {expected_status}, body: {body[:200]}")
            failed += 1
        else:
            passed += 1
        return ok

    print(f"\nTesting: {base_url}\n")

    # 1. Health check
    print("--- Project 1: Basic Flask ---")
    status, body = make_request(f"{base_url}/api/health")
    check("GET /api/health", status, body)

    # 2. Webhook test
    status, body = make_request(
        f"{base_url}/api/webhook-test",
        method="POST",
        data={"test_key": "test_value"},
        content_type="application/x-www-form-urlencoded",
    )
    check("POST /api/webhook-test", status, body)

    # 3. Session endpoints
    print("\n--- Project 2: Redis Sessions ---")
    caller = "%2B1234567890"  # URL-encoded +1234567890

    status, body = make_request(
        f"{base_url}/api/start-session?caller_id={caller}",
        method="POST",
        data={},
        content_type="application/x-www-form-urlencoded",
    )
    check("POST /api/start-session", status, body)

    status, body = make_request(f"{base_url}/api/get-session?caller_id={caller}")
    check("GET /api/get-session", status, body)

    status, body = make_request(
        f"{base_url}/api/update-session?caller_id={caller}&step=menu_selection",
        method="POST",
        data={},
        content_type="application/x-www-form-urlencoded",
    )
    check("POST /api/update-session", status, body)

    status, body = make_request(f"{base_url}/api/get-session?caller_id={caller}")
    check("GET /api/get-session (verify update)", status, body)
    if status == 200:
        data = json.loads(body)
        step = data.get("session", {}).get("step")
        if step == "menu_selection":
            print(f"         Step correctly updated to: {step}")
        else:
            print(f"         WARNING: Step is '{step}', expected 'menu_selection'")

    # 4. Database endpoints
    print("\n--- Project 3: Postgres Call Logs ---")

    status, body = make_request(f"{base_url}/api/setup-db")
    check("GET /api/setup-db", status, body)

    status, body = make_request(
        f"{base_url}/api/log-call",
        method="POST",
        data=json.dumps({
            "call_uuid": f"test-{int(__import__('time').time())}",
            "from_number": "+1234567890",
            "to_number": "+0987654321",
            "duration": 120,
            "call_status": "completed",
        }),
        content_type="application/json",
    )
    check("POST /api/log-call", status, body, expected_status=201)

    status, body = make_request(f"{base_url}/api/call-logs")
    check("GET /api/call-logs", status, body)

    status, body = make_request(f"{base_url}/api/call-history/1234567890")
    check("GET /api/call-history/<phone>", status, body)

    # 5. Seed menus
    print("\n--- Project 4: IVR Setup ---")
    status, body = make_request(
        f"{base_url}/api/seed-menus",
        method="POST",
        data={},
        content_type="application/x-www-form-urlencoded",
    )
    check("POST /api/seed-menus", status, body)

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*40}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_endpoints.py <base_url>")
        print("Example: python scripts/test_endpoints.py https://your-project.vercel.app")
        sys.exit(1)

    test_all(sys.argv[1])
