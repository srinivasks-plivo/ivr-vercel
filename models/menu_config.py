"""MenuConfiguration model - defines IVR menu structure."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON
from models.database import Base


class MenuConfiguration(Base):
    __tablename__ = "menu_configurations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    menu_id = Column(String(100), unique=True, nullable=False, index=True)
    parent_menu_id = Column(String(100), nullable=True, index=True)
    menu_type = Column(String(50), nullable=False, default='menu')
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    audio_url = Column(String(500), nullable=True)
    language = Column(String(10), nullable=False, default='en-US')
    voice = Column(String(50), nullable=False, default='WOMAN')
    max_digits = Column(Integer, nullable=False, default=1)
    timeout = Column(Integer, nullable=False, default=5)
    digit_actions = Column(JSON, nullable=True)
    invalid_input_menu_id = Column(String(100), nullable=True)
    timeout_menu_id = Column(String(100), nullable=True)
    action_type = Column(String(50), nullable=True)
    action_config = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    priority = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_digit_option(self, digit):
        if self.digit_actions and digit in self.digit_actions:
            return self.digit_actions[digit]
        return None

    def validate_digit(self, digit):
        if self.digit_actions:
            return digit in self.digit_actions
        return False

    def to_dict(self):
        return {
            'menu_id': self.menu_id,
            'title': self.title,
            'message': self.message,
            'max_digits': self.max_digits,
            'timeout': self.timeout,
            'digit_actions': self.digit_actions,
            'action_type': self.action_type,
            'is_active': self.is_active,
        }
