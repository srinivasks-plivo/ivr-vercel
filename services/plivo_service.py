"""
Plivo XML Service - Generates XML responses for Plivo Voice API.
Same as Day3 version, no changes needed for Vercel.
"""

from config import get_config

config = get_config()


class PlivoXMLService:
    """Generate Plivo XML responses for voice calls."""

    @staticmethod
    def _escape_xml(text):
        replacements = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;"}
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        return text

    @staticmethod
    def generate_menu_xml(message, timeout=None, max_digits=None, action_url="/api/handle-input"):
        if timeout is None:
            timeout = config.DEFAULT_TIMEOUT
        if max_digits is None:
            max_digits = 1

        xml = (
            '<Response>\n'
            f'  <GetDigits action="{action_url}" timeout="{timeout}" numDigits="{max_digits}">\n'
            f'    <Speak>{PlivoXMLService._escape_xml(message)}</Speak>\n'
            '  </GetDigits>\n'
            '</Response>'
        )
        return xml

    @staticmethod
    def generate_transfer_xml(phone_number, timeout=30, message=None):
        if message:
            xml = (
                '<Response>\n'
                f'  <Speak>{PlivoXMLService._escape_xml(message)}</Speak>\n'
                f'  <Dial timeout="{timeout}">\n'
                f'    <Number>{phone_number}</Number>\n'
                '  </Dial>\n'
                '</Response>'
            )
        else:
            xml = (
                '<Response>\n'
                f'  <Dial timeout="{timeout}">\n'
                f'    <Number>{phone_number}</Number>\n'
                '  </Dial>\n'
                '</Response>'
            )
        return xml

    @staticmethod
    def generate_hangup_xml(message=None):
        if message:
            xml = (
                '<Response>\n'
                f'  <Speak>{PlivoXMLService._escape_xml(message)}</Speak>\n'
                '  <Hangup />\n'
                '</Response>'
            )
        else:
            xml = (
                '<Response>\n'
                '  <Hangup />\n'
                '</Response>'
            )
        return xml

    @staticmethod
    def generate_invalid_input_xml(retry_count=None, max_retries=None):
        if max_retries is None:
            max_retries = config.MAX_RETRIES
        if retry_count and retry_count >= max_retries:
            message = "I didn't understand that. Your call is being transferred."
        else:
            message = "Invalid input. Please try again."
        return PlivoXMLService.generate_speak_only_xml(message)

    @staticmethod
    def generate_speak_only_xml(message):
        xml = (
            '<Response>\n'
            f'  <Speak>{PlivoXMLService._escape_xml(message)}</Speak>\n'
            '</Response>'
        )
        return xml


plivo_service = PlivoXMLService()
