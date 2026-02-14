"""
Vercel Serverless Flask App - IVR System

All routes are served through this single Flask app.
Vercel routes requests here via vercel.json rewrites.

Endpoints:
  GET  /api/health              - Health check (Redis + Postgres)
  POST /api/webhook-test        - Echo POST data (for testing)
  POST /api/start-session       - Create Redis session
  GET  /api/get-session         - Get session by caller_id
  POST /api/update-session      - Update session step
  GET  /api/setup-db            - Create database tables (run once)
  POST /api/seed-menus          - Seed default IVR menus (run once)
  POST /api/log-call            - Insert a call record
  GET  /api/call-logs           - Return all call logs as JSON
  GET  /api/call-history/<phone>- Return logs for a specific phone number
  POST /api/answer              - Plivo incoming call webhook
  POST /api/handle-input        - Plivo digit input webhook
  POST /api/hangup              - Plivo call hangup webhook
"""

import sys
import os
import json
import logging
from datetime import datetime

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, Response, jsonify

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================
# PROJECT 1: Basic Flask on Vercel
# =============================================

@app.route('/api/health', methods=['GET'])
def health():
    """Health check - tests Redis and Postgres connectivity."""
    result = {
        "status": "healthy",
        "redis": "ok",
        "postgres": "ok",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Test Redis
    try:
        from services.redis_service import get_redis_service
        redis_svc = get_redis_service()
        if not redis_svc.ping():
            result["redis"] = "error"
            result["status"] = "unhealthy"
    except Exception as e:
        result["redis"] = f"error: {str(e)}"
        result["status"] = "unhealthy"

    # Test Postgres
    try:
        from models.database import get_engine
        from sqlalchemy import text
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        result["postgres"] = f"error: {str(e)}"
        result["status"] = "unhealthy"

    status_code = 200 if result["status"] == "healthy" else 503
    return jsonify(result), status_code


@app.route('/api/webhook-test', methods=['POST'])
def webhook_test():
    """Echo back POST data - for testing webhooks."""
    data = {}

    # Try to get data from various content types
    if request.is_json:
        data = request.get_json()
    elif request.form:
        data = dict(request.form)
    else:
        data = {"raw_body": request.get_data(as_text=True)}

    return jsonify({
        "received": True,
        "method": request.method,
        "content_type": request.content_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    })


# =============================================
# PROJECT 2: Redis Session Management
# =============================================

@app.route('/api/start-session', methods=['POST'])
def start_session():
    """Create a new session in Redis."""
    caller_id = request.args.get('caller_id')
    if not caller_id:
        return jsonify({"error": "caller_id query parameter required"}), 400

    from services.redis_service import get_redis_service
    redis_svc = get_redis_service()

    # Use caller_id as a simple session key
    session_data = {
        "step": "greeting",
        "started_at": datetime.utcnow().isoformat(),
        "caller_id": caller_id,
    }

    import json as json_mod
    from services.redis_service import _get_redis
    client = _get_redis()
    from config import get_config
    config = get_config()
    session_key = f"session:{caller_id}"
    client.setex(session_key, config.SESSION_TTL, json_mod.dumps(session_data))

    return jsonify({
        "message": "Session created",
        "session": session_data,
        "ttl_seconds": config.SESSION_TTL,
    })


@app.route('/api/get-session', methods=['GET'])
def get_session_endpoint():
    """Get session by caller_id."""
    caller_id = request.args.get('caller_id')
    if not caller_id:
        return jsonify({"error": "caller_id query parameter required"}), 400

    import json as json_mod
    from services.redis_service import _get_redis
    client = _get_redis()
    session_key = f"session:{caller_id}"
    session_json = client.get(session_key)

    if session_json is None:
        return jsonify({"error": "Session not found or expired"}), 404

    session_data = json_mod.loads(session_json) if isinstance(session_json, str) else session_json
    return jsonify({"session": session_data})


@app.route('/api/update-session', methods=['POST'])
def update_session():
    """Update session step for a caller."""
    caller_id = request.args.get('caller_id')
    step = request.args.get('step')
    if not caller_id or not step:
        return jsonify({"error": "caller_id and step query parameters required"}), 400

    import json as json_mod
    from services.redis_service import _get_redis
    client = _get_redis()
    from config import get_config
    config = get_config()

    session_key = f"session:{caller_id}"
    session_json = client.get(session_key)

    if session_json is None:
        return jsonify({"error": "Session not found or expired"}), 404

    session_data = json_mod.loads(session_json) if isinstance(session_json, str) else session_json
    session_data["step"] = step
    session_data["updated_at"] = datetime.utcnow().isoformat()

    client.setex(session_key, config.SESSION_TTL, json_mod.dumps(session_data))

    return jsonify({"message": "Session updated", "session": session_data})


# =============================================
# PROJECT 3: Postgres Call Logs
# =============================================

@app.route('/api/setup-db', methods=['GET'])
def setup_db():
    """Create database tables. Run once after connecting Postgres."""
    try:
        from models import init_db
        init_db()
        return jsonify({"message": "Table created successfully"})
    except Exception as e:
        logger.error(f"setup-db error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/seed-menus', methods=['POST'])
def seed_menus():
    """Seed the default IVR menu structure."""
    try:
        from models.database import get_session as db_session
        from models.menu_config import MenuConfiguration
        from config import get_config
        config = get_config()

        db = db_session()
        try:
            # Delete existing menus
            db.query(MenuConfiguration).delete()
            db.commit()

            # Main Menu
            db.add(MenuConfiguration(
                menu_id='main_menu',
                parent_menu_id=None,
                title='Main Menu',
                message='Welcome. Press 1 for Sales, or Press 2 for Support.',
                digit_actions={'1': 'sales_transfer', '2': 'support_transfer'},
                action_type='menu',
            ))

            # Sales Transfer
            db.add(MenuConfiguration(
                menu_id='sales_transfer',
                parent_menu_id='main_menu',
                title='Sales Transfer',
                message='Connecting you to Sales. Please hold.',
                action_type='transfer',
                action_config={'transfer_number': config.SALES_TRANSFER_NUMBER or '+1234567890'},
            ))

            # Support Transfer
            db.add(MenuConfiguration(
                menu_id='support_transfer',
                parent_menu_id='main_menu',
                title='Support Transfer',
                message='Connecting you to Support. Please hold.',
                action_type='transfer',
                action_config={'transfer_number': config.SUPPORT_TRANSFER_NUMBER or '+1234567890'},
            ))

            # Invalid Input
            db.add(MenuConfiguration(
                menu_id='invalid_input',
                parent_menu_id='main_menu',
                title='Invalid Input',
                message='Invalid input. Press 1 for Sales, or Press 2 for Support.',
                digit_actions={'1': 'sales_transfer', '2': 'support_transfer'},
                action_type='menu',
            ))

            db.commit()

            menus = db.query(MenuConfiguration).all()
            return jsonify({
                "message": f"Seeded {len(menus)} menus successfully",
                "menus": [m.to_dict() for m in menus],
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"seed-menus error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/log-call', methods=['POST'])
def log_call():
    """Insert a call record into Postgres."""
    try:
        data = request.get_json() if request.is_json else dict(request.form)

        from models.database import get_session as db_session
        from models.call_log import CallLog

        db = db_session()
        try:
            call_log = CallLog(
                call_uuid=data.get('call_uuid', f"manual-{datetime.utcnow().timestamp()}"),
                from_number=data.get('from_number', 'unknown'),
                to_number=data.get('to_number', 'unknown'),
                start_time=datetime.utcnow(),
                duration=int(data.get('duration', 0)),
                call_status=data.get('call_status', 'completed'),
                hangup_cause=data.get('hangup_cause', 'NORMAL_CLEARING'),
                menu_path=data.get('menu_path'),
                user_inputs=data.get('user_inputs'),
            )
            db.add(call_log)
            db.commit()

            return jsonify({"message": "Call logged", "call": call_log.to_dict()}), 201
        finally:
            db.close()

    except Exception as e:
        logger.error(f"log-call error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/call-logs', methods=['GET'])
def call_logs():
    """Return all call logs as JSON."""
    try:
        from models.database import get_session as db_session
        from models.call_log import CallLog

        db = db_session()
        try:
            logs = db.query(CallLog).order_by(CallLog.start_time.desc()).limit(100).all()
            return jsonify({
                "count": len(logs),
                "logs": [log.to_dict() for log in logs],
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"call-logs error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/call-history/<phone>', methods=['GET'])
def call_history(phone):
    """Return call logs for a specific phone number."""
    try:
        from models.database import get_session as db_session
        from models.call_log import CallLog

        # Handle URL-encoded + sign
        if not phone.startswith('+'):
            phone = f"+{phone}"

        db = db_session()
        try:
            logs = db.query(CallLog).filter_by(from_number=phone).order_by(CallLog.start_time.desc()).all()
            return jsonify({
                "phone": phone,
                "count": len(logs),
                "logs": [log.to_dict() for log in logs],
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"call-history error: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================
# PROJECT 4: Full IVR Webhooks
# =============================================

@app.route('/api/answer', methods=['POST'])
def answer():
    """Plivo calls this on incoming call."""
    try:
        call_uuid = request.form.get('CallUUID')
        from_number = request.form.get('From')
        to_number = request.form.get('To')

        logger.info(f"ANSWER: CallUUID={call_uuid}, From={from_number}, To={to_number}")

        if not call_uuid or not from_number or not to_number:
            error_xml = '<Response><Speak>Invalid call parameters</Speak><Hangup /></Response>'
            return Response(error_xml, mimetype='application/xml')

        from services.ivr_service import get_ivr_service
        ivr = get_ivr_service()
        xml_response = ivr.handle_incoming_call(call_uuid, from_number, to_number)

        return Response(xml_response, mimetype='application/xml')

    except Exception as e:
        logger.error(f"Answer error: {e}", exc_info=True)
        error_xml = '<Response><Speak>An error occurred. Please try again later.</Speak><Hangup /></Response>'
        return Response(error_xml, mimetype='application/xml')


@app.route('/api/handle-input', methods=['POST'])
def handle_input():
    """Plivo calls this when user presses a digit."""
    try:
        call_uuid = request.form.get('CallUUID')
        digits = request.form.get('Digits')

        logger.info(f"INPUT: CallUUID={call_uuid}, Digits={digits}")

        if not call_uuid or not digits:
            error_xml = '<Response><Speak>Invalid input parameters</Speak></Response>'
            return Response(error_xml, mimetype='application/xml')

        from services.ivr_service import get_ivr_service
        ivr = get_ivr_service()
        xml_response = ivr.handle_digit_input(call_uuid, digits)

        return Response(xml_response, mimetype='application/xml')

    except Exception as e:
        logger.error(f"Handle-input error: {e}", exc_info=True)
        error_xml = '<Response><Speak>An error occurred processing your input.</Speak></Response>'
        return Response(error_xml, mimetype='application/xml')


@app.route('/api/hangup', methods=['POST'])
def hangup():
    """Plivo calls this when the call ends."""
    try:
        call_uuid = request.form.get('CallUUID')
        hangup_cause = request.form.get('HangupCause')
        duration = request.form.get('Duration', 0)

        logger.info(f"HANGUP: CallUUID={call_uuid}, Cause={hangup_cause}, Duration={duration}s")

        if not call_uuid:
            return Response('', status=400)

        try:
            duration = int(duration)
        except (ValueError, TypeError):
            duration = 0

        from services.ivr_service import get_ivr_service
        ivr = get_ivr_service()
        ivr.handle_hangup(call_uuid, hangup_cause, duration)

        return Response('', status=200)

    except Exception as e:
        logger.error(f"Hangup error: {e}", exc_info=True)
        return Response('', status=200)


# =============================================
# Root endpoint
# =============================================

@app.route('/', methods=['GET'])
@app.route('/api', methods=['GET'])
def index():
    """Root info page."""
    return jsonify({
        "app": "IVR System on Vercel",
        "status": "running",
        "endpoints": {
            "GET /api/health": "Health check (Redis + Postgres)",
            "POST /api/webhook-test": "Echo POST data",
            "POST /api/start-session": "Create Redis session (?caller_id=...)",
            "GET /api/get-session": "Get session (?caller_id=...)",
            "POST /api/update-session": "Update session (?caller_id=...&step=...)",
            "GET /api/setup-db": "Create database tables (run once)",
            "POST /api/seed-menus": "Seed IVR menus (run once)",
            "POST /api/log-call": "Insert call record",
            "GET /api/call-logs": "List all call logs",
            "GET /api/call-history/<phone>": "Call logs for phone number",
            "POST /api/answer": "Plivo incoming call webhook",
            "POST /api/handle-input": "Plivo digit input webhook",
            "POST /api/hangup": "Plivo call hangup webhook",
        }
    })
