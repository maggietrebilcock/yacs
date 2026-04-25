from sqlalchemy.orm import Session
from datetime import datetime

from models.user_session import UserSession


def create_session(db: Session, user_id: int) -> UserSession:
    """Creates and saves a new user session."""
    new_session = UserSession(user_id=user_id, start_time=datetime.utcnow())
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


def get_session(db: Session, session_id: str) -> UserSession | None:
    """Gets a session by its ID."""
    return db.query(UserSession).filter(UserSession.session_id == session_id).first()


def end_session(db: Session, session_id: str) -> UserSession | None:
    """Finds a session and sets its end time."""
    session_to_end = get_session(db, session_id)
    if session_to_end:
        session_to_end.end_time = datetime.utcnow()
        db.commit()
        db.refresh(session_to_end)
    return session_to_end
