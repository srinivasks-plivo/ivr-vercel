"""
Redis Service for Vercel - Uses Upstash REST API.

Unlike the local version that uses redis-py TCP connections,
this uses the Upstash REST API which works in serverless environments.
Vercel auto-configures KV_REST_API_URL and KV_REST_API_TOKEN when you
connect Redis via the Storage tab.
"""

import json
import logging
from datetime import datetime
from upstash_redis import Redis
from config import get_config

logger = logging.getLogger(__name__)

# Lazy-initialized Redis client
_redis_client = None


def _get_redis():
    """Get or create Upstash Redis client."""
    global _redis_client
    if _redis_client is None:
        config = get_config()
        if not config.KV_REST_API_URL or not config.KV_REST_API_TOKEN:
            raise RuntimeError(
                "KV_REST_API_URL and KV_REST_API_TOKEN not set. "
                "Connect Redis via Vercel Storage tab."
            )
        _redis_client = Redis(
            url=config.KV_REST_API_URL,
            token=config.KV_REST_API_TOKEN,
        )
    return _redis_client


class RedisSessionService:
    """Manage call sessions in Upstash Redis via REST API."""

    def __init__(self):
        self.config = get_config()

    def _get_client(self):
        return _get_redis()

    # ===== SESSION CRUD =====

    def create_session(self, call_uuid, from_number, to_number):
        """Create a new call session with TTL."""
        session_data = {
            "call_uuid": call_uuid,
            "from_number": from_number,
            "to_number": to_number,
            "current_menu_id": "main_menu",
            "menu_history": ["main_menu"],
            "user_inputs": [],
            "start_time": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "state": "active",
        }

        session_key = f"ivr:session:{call_uuid}"
        client = self._get_client()
        client.setex(session_key, self.config.SESSION_TTL, json.dumps(session_data))

        logger.info(f"Session created: {call_uuid}")
        return session_data

    def get_session(self, call_uuid):
        """Retrieve a session from Redis."""
        session_key = f"ivr:session:{call_uuid}"
        client = self._get_client()
        session_json = client.get(session_key)

        if session_json is None:
            logger.warning(f"Session not found: {call_uuid}")
            return None

        # upstash-redis may return a string directly
        if isinstance(session_json, str):
            return json.loads(session_json)
        return session_json

    def update_session(self, call_uuid, updates):
        """Update an existing session."""
        session = self.get_session(call_uuid)
        if session is None:
            return None

        session.update(updates)
        session["last_activity"] = datetime.utcnow().isoformat()

        session_key = f"ivr:session:{call_uuid}"
        client = self._get_client()
        client.setex(session_key, self.config.SESSION_TTL, json.dumps(session))

        return session

    def delete_session(self, call_uuid):
        """Delete a session (cleanup after call ends)."""
        session_key = f"ivr:session:{call_uuid}"
        client = self._get_client()
        result = client.delete(session_key)
        return result > 0 if isinstance(result, int) else bool(result)

    # ===== SESSION MANIPULATION =====

    def add_user_input(self, call_uuid, menu_id, digit):
        """Record a digit press."""
        session = self.get_session(call_uuid)
        if session is None:
            return None

        input_record = {
            "menu_id": menu_id,
            "digit": digit,
            "timestamp": datetime.utcnow().isoformat(),
        }
        session["user_inputs"].append(input_record)
        return self.update_session(call_uuid, {"user_inputs": session["user_inputs"]})

    def set_current_menu(self, call_uuid, menu_id):
        """Change the current menu for a call."""
        session = self.get_session(call_uuid)
        if session is None:
            return None

        session["menu_history"].append(menu_id)
        return self.update_session(call_uuid, {
            "current_menu_id": menu_id,
            "menu_history": session["menu_history"],
        })

    def mark_call_completed(self, call_uuid):
        """Mark a call as completed."""
        return self.update_session(call_uuid, {"state": "completed"})

    # ===== HEALTH CHECK =====

    def ping(self):
        """Test Redis connectivity."""
        try:
            client = self._get_client()
            result = client.ping()
            return result == "PONG" or result is True
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False


# Lazy singleton - created on first use
_service_instance = None


def get_redis_service():
    """Get the Redis service singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = RedisSessionService()
    return _service_instance
