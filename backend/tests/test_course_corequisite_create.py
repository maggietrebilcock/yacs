"""Quick runtime test to import CourseCorequisite and create its table in SQLite.

This test loads the model files by path so it doesn't execute
`backend/tables/__init__.py` (which creates a PostgreSQL engine and requires
psycopg). Run from the repository root with:
    /path/to/venv/bin/python backend/tests/test_course_corequisite_create.py
"""
import os
import pathlib
import importlib.util
import sys
import types
from sqlalchemy import create_engine, inspect


def load_module_as(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Locate the backend/tables directory relative to this test file
tables_dir = pathlib.Path(__file__).resolve().parents[1] / 'tables'

# Create a lightweight package module for 'tables' so relative imports inside
# the model files (e.g. `from .database import Base`) resolve correctly when
# we load the files directly.
tables_pkg = types.ModuleType('tables')
tables_pkg.__path__ = [str(tables_dir)]
sys.modules['tables'] = tables_pkg

# Load database and model modules under the 'tables' package name
db_mod = load_module_as('tables.database', str(tables_dir / 'database.py'))
sys.modules['tables.database'] = db_mod
cc_mod = load_module_as('tables.course_corequisite', str(tables_dir / 'course_corequisite.py'))
sys.modules['tables.course_corequisite'] = cc_mod

Base = db_mod.Base
CourseCorequisite = cc_mod.CourseCorequisite

# Use a temporary SQLite file in repo
db_path = 'backend/tests/tmp_test_db.sqlite'
if os.path.exists(db_path):
    os.remove(db_path)

engine = create_engine(f'sqlite:///{db_path}')

# Create tables
Base.metadata.create_all(engine)

inspector = inspect(engine)
print('Tables in test DB:', inspector.get_table_names())

# Check columns for course_corequisite
if 'course_corequisite' in inspector.get_table_names():
    cols = inspector.get_columns('course_corequisite')
    print('Columns for course_corequisite:')
    for c in cols:
        print(f" - {c['name']} : {c['type']}")
else:
    raise SystemExit('ERROR: course_corequisite table not created')

print('SUCCESS: course_corequisite model imported and table created in SQLite')
