# src/api/db/course_corequisite.py

class CourseCorequisite:
    def __init__(self, db_conn):
        self.db = db_conn

    def add_corequisite(self, department, level, corequisite):
        sql = """
            INSERT INTO course_corequisite (department, level, corequisite)
            VALUES (%s, %s, %s)
        """
        args = (department, level, corequisite)
        _, error = self.db.execute(sql, args, isSELECT=False)
        return (True, None) if not error else (False, error)

    def get_corequisites(self, department, level):
        sql = """
            SELECT corequisite
            FROM course_corequisite
            WHERE department = %s AND level = %s
        """
        args = (department, level)
        result, error = self.db.execute(sql, args)
        return (result, None) if not error else (None, error)
    