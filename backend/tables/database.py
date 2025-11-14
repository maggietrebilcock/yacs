from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

engine = create_engine('postgresql://yacs:yacs@db:5432/yacsdb')
Base.metadata.create_all(bind=engine)