from sqlalchemy import Column, PrimaryKeyConstraint, String, Integer

from .database import Base


class CourseCorequisite(Base):
	__tablename__ = 'course_corequisite'

	department = Column(String(length=255))
	level = Column(Integer)
	corequisite = Column(String(length=255))

	__table_args__ = (
		PrimaryKeyConstraint('department', 'level', 'corequisite'),
	)

