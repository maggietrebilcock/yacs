from sqlalchemy import Column, String, DateTime, Integer
import uuid

from .database import Base


class UserSession(Base):
    __tablename__ = 'user_session'

    session_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, nullable=False)  # TODO: Add ForeignKey('users.id') when User model exists
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
