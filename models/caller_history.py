"""CallerHistory model - aggregated info about each caller."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON
from models.database import Base


class CallerHistory(Base):
    __tablename__ = "caller_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    first_call_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_call_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_calls = Column(Integer, nullable=False, default=1)
    total_duration = Column(Integer, nullable=False, default=0)
    preferred_language = Column(String(10), nullable=True, default='en')
    last_menu_completed = Column(String(100), nullable=True)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        avg_duration = self.total_duration / self.total_calls if self.total_calls > 0 else 0
        return {
            'phone_number': self.phone_number,
            'total_calls': self.total_calls,
            'total_duration': self.total_duration,
            'average_duration': avg_duration,
            'first_call_at': self.first_call_at.isoformat() if self.first_call_at else None,
            'last_call_at': self.last_call_at.isoformat() if self.last_call_at else None,
            'preferred_language': self.preferred_language,
            'is_returning_caller': self.total_calls > 1,
        }
