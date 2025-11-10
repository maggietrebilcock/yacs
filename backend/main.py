#!/usr/bin/python3
from fastapi import FastAPI, Request, Response
from starlette.middleware.sessions import SessionMiddleware
import os

# Import Pydantic models and controllers
from api_models import UserPydantic, SessionPydantic
from controllers import user_controller, session_controller
from tables.api_models import CourseCorequisiteCreate
from db.course_corequisite import CourseCorequisite
from db import database



# --- Initialize FastAPI App ---
app = FastAPI()

# --- Add Middleware ---
app.add_middleware(SessionMiddleware, secret_key="a_very_secret_key")

# --- Add Helper Db Connection ---
db_conn = database.db
course_corequisite = CourseCorequisite(db_conn)


# --- API Endpoints ---

@app.get('/')
async def root():
    """Confirms the API is running."""
    return {"message": "YACS API is Up!"}

## User Account Management ##
@app.post('/api/user')
async def add_user(user: UserPydantic):
    return user_controller.create_user(user.dict())

@app.delete('/api/user')
async def delete_user(request: Request):
    if 'user' not in request.session:
        return Response("Not authorized", status_code=403)
    user_id = request.session['user']['user_id']
    return user_controller.delete_current_user(user_id)

## Session Management (Login/Logout) ##
@app.post('/api/session')
async def log_in(request: Request, credentials: SessionPydantic):
    return session_controller.log_user_in(credentials.dict(), request.session)

@app.delete('/api/session')
def log_out(request: Request):
    return session_controller.log_user_out(request.session)

# --- Add your Course, Professor, and other endpoints below ---
# Example:
# from controllers import course_controller
#
# @app.get('/api/semester')
# async def get_semesters():
#     return course_controller.get_all_semesters()

@app.post('/api/corequisite')
async def add_corequisite(coreq: CourseCorequisiteCreate):
    success, error = course_corequisite.add_corequisite(
        coreq.department, coreq.level, coreq.corequisite
    )
    if success:
        return {"message": "Corequisite added successfully"}
    else:
        return Response(content=str(error), status_code=500)


@app.get('/api/corequisite/{department}/{level}')
async def get_corequisites(department: str, level: int):
    result, error = course_corequisite.get_corequisites(department, level)
    if error:
        return Response(content=str(error), status_code=500)
    return result
