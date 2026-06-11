from sqlalchemy.orm import Session
from typing import List

from models.course_corequisite import CourseCorequisite


def add_corequisite(db: Session, department: str, level: int, corequisite: str) -> CourseCorequisite:
    """Adds a new corequisite relationship."""
    new_coreq = CourseCorequisite(
        department=department,
        level=level,
        corequisite=corequisite
    )
    db.add(new_coreq)
    db.commit()
    db.refresh(new_coreq)
    return new_coreq


def get_corequisites(db: Session, department: str, level: int) -> List[CourseCorequisite]:
    """Gets all corequisites for a course by department and level."""
    return db.query(CourseCorequisite).filter(
        CourseCorequisite.department == department,
        CourseCorequisite.level == level
    ).all()
