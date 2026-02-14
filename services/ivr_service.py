"""
IVR Service - Orchestrates the IVR call flow on Vercel.

Adapted from Day3: uses lazy-initialized Redis and per-request DB sessions.
"""

import logging
from datetime import datetime, timedelta
from models.database import get_session
from models.menu_config import MenuConfiguration
from models.call_log import CallLog
from models.caller_history import CallerHistory
from services.redis_service import get_redis_service
from services.plivo_service import plivo_service
from config import get_config

logger = logging.getLogger(__name__)


class IVRService:
    """Orchestrate the IVR call flow."""

    def __init__(self):
        self.config = get_config()

    @property
    def redis(self):
        return get_redis_service()

    def handle_incoming_call(self, call_uuid, from_number, to_number):
        """Handle incoming call: create session, return main menu XML."""
        logger.info(f"INCOMING CALL: {from_number}")

        # Create session in Redis
        self.redis.create_session(call_uuid, from_number, to_number)

        # Load main menu from database
        menu = self._get_menu_config("main_menu")
        if menu is None:
            logger.error("main_menu not found in database!")
            return plivo_service.generate_hangup_xml(
                "Sorry, our system is unavailable. Please try later."
            )

        # Build the action URL using Vercel deployment URL
        base_url = self.config.WEBHOOK_BASE_URL
        action_url = f"{base_url}/api/handle-input" if base_url else "/api/handle-input"

        xml = plivo_service.generate_menu_xml(
            message=menu.message,
            timeout=menu.timeout,
            max_digits=menu.max_digits,
            action_url=action_url,
        )
        return xml

    def handle_digit_input(self, call_uuid, digit):
        """Handle user pressing a digit."""
        logger.info(f"DIGIT INPUT: {digit}")

        # Get session
        session = self.redis.get_session(call_uuid)
        if session is None:
            return plivo_service.generate_hangup_xml("Your session has expired. Please call back.")

        # Get current menu
        current_menu_id = session["current_menu_id"]
        menu = self._get_menu_config(current_menu_id)
        if menu is None:
            return plivo_service.generate_hangup_xml("System error. Please try later.")

        # Validate digit
        if not menu.validate_digit(digit):
            invalid_menu_id = menu.invalid_input_menu_id
            if invalid_menu_id:
                invalid_menu = self._get_menu_config(invalid_menu_id)
                if invalid_menu:
                    base_url = self.config.WEBHOOK_BASE_URL
                    action_url = f"{base_url}/api/handle-input" if base_url else "/api/handle-input"
                    return plivo_service.generate_menu_xml(
                        message=invalid_menu.message,
                        timeout=invalid_menu.timeout,
                        action_url=action_url,
                    )
            return plivo_service.generate_invalid_input_xml()

        # Record input
        self.redis.add_user_input(call_uuid, current_menu_id, digit)

        # Determine next action
        next_menu_id = menu.get_digit_option(digit)
        if not next_menu_id:
            return plivo_service.generate_hangup_xml("Thank you for calling.")

        next_menu = self._get_menu_config(next_menu_id)
        if next_menu is None:
            return plivo_service.generate_hangup_xml("System error.")

        # Generate response based on next menu's action type
        if next_menu.action_type == "transfer":
            transfer_number = next_menu.action_config.get("transfer_number") if next_menu.action_config else None
            if not transfer_number:
                return plivo_service.generate_hangup_xml("Transfer configuration error.")
            transfer_timeout = next_menu.action_config.get("timeout", 30)
            self.redis.set_current_menu(call_uuid, next_menu_id)
            return plivo_service.generate_transfer_xml(
                phone_number=transfer_number,
                timeout=transfer_timeout,
                message=next_menu.message,
            )

        elif next_menu.action_type == "hangup":
            return plivo_service.generate_hangup_xml(next_menu.message)

        else:
            # Navigate to next menu
            self.redis.set_current_menu(call_uuid, next_menu_id)
            base_url = self.config.WEBHOOK_BASE_URL
            action_url = f"{base_url}/api/handle-input" if base_url else "/api/handle-input"
            return plivo_service.generate_menu_xml(
                message=next_menu.message,
                timeout=next_menu.timeout,
                max_digits=next_menu.max_digits,
                action_url=action_url,
            )

    def handle_hangup(self, call_uuid, hangup_cause=None, duration=None):
        """Handle call end: save to DB, cleanup Redis."""
        logger.info(f"CALL HANGUP: {call_uuid}")

        session = self.redis.get_session(call_uuid)
        if session is None:
            logger.warning("Session already expired/deleted")
            return

        self.redis.mark_call_completed(call_uuid)
        self._save_call_to_database(call_uuid, session, hangup_cause, duration)
        self._update_caller_history(session["from_number"], duration)
        self.redis.delete_session(call_uuid)

    # ===== HELPERS =====

    def _get_menu_config(self, menu_id):
        """Load menu configuration from database."""
        db = get_session()
        try:
            return db.query(MenuConfiguration).filter_by(menu_id=menu_id).first()
        finally:
            db.close()

    def _save_call_to_database(self, call_uuid, session, hangup_cause, duration):
        """Save call data to CallLog table."""
        db = get_session()
        try:
            start_time = datetime.fromisoformat(session["start_time"])
            end_time = start_time + timedelta(seconds=duration) if duration else datetime.utcnow()

            call_log = CallLog(
                call_uuid=call_uuid,
                from_number=session["from_number"],
                to_number=session["to_number"],
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                menu_path=session.get("menu_history"),
                user_inputs=session.get("user_inputs"),
                call_status="completed",
                hangup_cause=hangup_cause,
            )
            db.add(call_log)
            db.commit()
            logger.info(f"Saved call to CallLog: {call_uuid}")
        except Exception as e:
            logger.error(f"Error saving call: {e}")
            db.rollback()
        finally:
            db.close()

    def _update_caller_history(self, phone_number, duration):
        """Update caller history with new call data."""
        db = get_session()
        try:
            caller = db.query(CallerHistory).filter_by(phone_number=phone_number).first()
            if caller:
                caller.total_calls += 1
                if duration:
                    caller.total_duration += duration
                caller.last_call_at = datetime.utcnow()
            else:
                caller = CallerHistory(
                    phone_number=phone_number,
                    first_call_at=datetime.utcnow(),
                    last_call_at=datetime.utcnow(),
                    total_calls=1,
                    total_duration=duration or 0,
                )
                db.add(caller)
            db.commit()
        except Exception as e:
            logger.error(f"Error updating caller history: {e}")
            db.rollback()
        finally:
            db.close()


# Lazy singleton
_ivr_instance = None


def get_ivr_service():
    global _ivr_instance
    if _ivr_instance is None:
        _ivr_instance = IVRService()
    return _ivr_instance
