"""CallLog model - stores information about each completed call."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from models.database import Base


class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_uuid = Column(String(255), unique=True, nullable=False, index=True)
    from_number = Column(String(20), nullable=False, index=True)
    to_number = Column(String(20), nullable=False)
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    answer_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)
    call_status = Column(String(50), nullable=False, default='active')
    hangup_cause = Column(String(100), nullable=True)
    menu_path = Column(JSON, nullable=True)
    user_inputs = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'call_uuid': self.call_uuid,
            'from_number': self.from_number,
            'to_number': self.to_number,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': self.duration,
            'call_status': self.call_status,
            'hangup_cause': self.hangup_cause,
            'menu_path': self.menu_path,
            'user_inputs': self.user_inputs,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
