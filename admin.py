from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqlalchemy import Column, Integer, String, TIMESTAMP, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from fastapi import Depends
import uvicorn
from sqlalchemy import Enum, BigInteger, Text, Boolean
from sqlalchemy import Date,Float

from config import Config

# Database setup
DATABASE_URL = Config.DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define your models
class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=True)
    password_hash = Column(String(200), nullable=True)
    is_superadmin = Column(Boolean, nullable=True)

class View(Base):
    __tablename__ = "views"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36))  # Matches char(36) in the table
    song_id = Column(String(10))  # Matches char(10) in the table
    view_count = Column(Integer, default=1)  # Matches int in the table, default is 1
    progress = Column( default=0.00)  # Matches decimal(5,2) in the table
    last_viewed = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP", onupdate="CURRENT_TIMESTAMP")  # Matches timestamp with default


class Download(Base):
    __tablename__ = "downloads"

    download_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(36), nullable=False)
    song_id = Column(String(36), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_format = Column(String(50), nullable=False)
    itag = Column(String(50), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_source = Column(String(50), nullable=False)
    download_status = Column(
        Enum("SUCCESS", "FAILED", "IN_PROGRESS"),
        default="IN_PROGRESS",
        nullable=True
    )
    user_agent = Column(Text, nullable=True)
    timestamp = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP", nullable=True)
    retries = Column(Integer, default=0)
    failure_reason = Column(Text, nullable=True)
    is_partial = Column(Boolean, default=False)
    thumbnail = Column(String(255), nullable=False)


class InjustifyUser(Base):
    __tablename__ = "injustifyusers"

    email = Column(String(255), nullable=False, unique=True)
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    picture = Column(String(855), nullable=True)
    verified_email = Column(Boolean, default=False)
    password = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP", nullable=True)
    updated_at = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP", onupdate="CURRENT_TIMESTAMP", nullable=True)
    status = Column(Enum("active", "inactive"), default="active", nullable=True)
    last_login = Column(TIMESTAMP, nullable=True)

class InjustifyMusic(Base):
    __tablename__ = "injustifymusic"

    song_id = Column(String(10), primary_key=True)
    title = Column(String(255), nullable=False, index=True)
    artist = Column(String(255), nullable=False)
    album = Column(String(255), nullable=True)
    genre = Column(String(100), nullable=True)
    release_date = Column(Date, nullable=True)
    duration = Column(Float, nullable=True)
    url = Column(String(500), nullable=True)
    upload_date = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP", nullable=True)
    is_favorite = Column(Boolean, default=False)
    views = Column(Integer, default=0)
    dislike = Column(Integer, nullable=True)
    thumbnail_path = Column(String(255), nullable=True)


class Playlist(Base):
    __tablename__ = "playlists"

    playlist_id = Column(String(10), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(String(36), nullable=False)
    created_at = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP", nullable=True)
    updated_at = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP", onupdate="CURRENT_TIMESTAMP", nullable=True)



class PlaylistSong(Base):
    __tablename__ = "playlistsongs"

    playlist_song_id = Column(Integer, primary_key=True, autoincrement=True)
    playlist_id = Column(String(10), nullable=False)
    song_id = Column(String(10), nullable=False)
    added_at = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP", nullable=True)


class VerificationSession(Base):
    __tablename__ = "verification_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False)
    token = Column(String(255), nullable=False, unique=True)
    expires_at = Column(TIMESTAMP, nullable=False)

# FastAPI app
app = FastAPI()

# Admin panel setup
admin = Admin(app, engine=engine)

from sqladmin import ModelView
from sqlalchemy import desc
class AdminUserView(ModelView, model=AdminUser):
    column_sortable_list = [AdminUser.id]
    column_default_sort = (AdminUser.id, False)  # Sort descending by default

class ViewModelView(ModelView, model=View):
    column_sortable_list = [View.last_viewed]  # Make sure column is sortable
    column_default_sort = (View.last_viewed, True)  # True = descending (most recent first)

class DownloadModelView(ModelView, model=Download):
    column_sortable_list = [Download.timestamp]
    column_default_sort = (Download.timestamp, True)  # Sort by most recent

class InjustifyUserView(ModelView, model=InjustifyUser):
    column_sortable_list = [InjustifyUser.created_at]
    column_default_sort = (InjustifyUser.created_at, True)

class InjustifyMusicView(ModelView, model=InjustifyMusic):
    column_sortable_list = [InjustifyMusic.upload_date]
    column_default_sort = (InjustifyMusic.upload_date, True)

class PlaylistView(ModelView, model=Playlist):
    column_sortable_list = [Playlist.created_at]
    column_default_sort = (Playlist.created_at, True)

class PlaylistSongView(ModelView, model=PlaylistSong):
    column_sortable_list = [PlaylistSong.added_at]
    column_default_sort = (PlaylistSong.added_at, True)

class VerificationSessionView(ModelView, model=VerificationSession):
    column_sortable_list = [VerificationSession.expires_at]
    column_default_sort = (VerificationSession.expires_at, False)

admin.add_view(AdminUserView)
admin.add_view(ViewModelView)
admin.add_view(DownloadModelView)
admin.add_view(InjustifyUserView)
admin.add_view(InjustifyMusicView)
admin.add_view(PlaylistView)
admin.add_view(PlaylistSongView)
admin.add_view(VerificationSessionView)


# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Run your FastAPI app to serve the admin panel
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)



    
# from fastapi import FastAPI, Depends, HTTPException, Request
# from fastapi.security import HTTPBearer, OAuth2PasswordBearer
# from sqladmin import Admin, ModelView
# from sqlalchemy import Column, Integer, String, TIMESTAMP, create_engine, Enum, BigInteger, Text, Boolean, Date, Float, func
# from sqlalchemy.orm import declarative_base, sessionmaker
# from passlib.context import CryptContext
# from datetime import datetime, timedelta
# from jose import JWTError, jwt
# from typing import Optional
# import uvicorn
# from starlette.middleware.sessions import SessionMiddleware
# from pydantic import BaseModel
# import secrets
# import logging

# # --------------------------
# # Configuration
# # --------------------------
# SECRET_KEY = secrets.token_hex(32)
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 30
# ADMIN_SESSION_TIMEOUT = 3600  # 1 hour

# # Database setup
# DATABASE_URL = "mysql+pymysql://root:0000@localhost/injustify"
# engine = create_engine(DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base()

# # Security setup
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# security = HTTPBearer()
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# # --------------------------
# # Models
# # --------------------------
# class AdminUser(Base):
#     __tablename__ = "admin_users"
    
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     username = Column(String(100), unique=True, nullable=False)
#     password_hash = Column(String(200), nullable=False)
#     email = Column(String(255), unique=True, nullable=False)
#     is_superadmin = Column(Boolean, default=False)
#     is_active = Column(Boolean, default=True)
#     last_login = Column(TIMESTAMP, nullable=True)
#     created_at = Column(TIMESTAMP, server_default=func.now())
#     updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
#     two_factor_enabled = Column(Boolean, default=False)
#     role = Column(Enum('admin', 'editor', 'viewer'), default='admin')

# class AdminAuditLog(Base):
#     __tablename__ = "admin_audit_logs"
    
#     id = Column(BigInteger, primary_key=True, autoincrement=True)
#     admin_id = Column(Integer, nullable=False)
#     action = Column(String(100), nullable=False)
#     entity_type = Column(String(50), nullable=True)
#     entity_id = Column(String(36), nullable=True)
#     ip_address = Column(String(45), nullable=True)
#     user_agent = Column(Text, nullable=True)
#     details = Column(Text, nullable=True)
#     created_at = Column(TIMESTAMP, server_default=func.now())

# class View(Base):
#     __tablename__ = "views"
    
#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(String(36))
#     song_id = Column(String(10))
#     view_count = Column(Integer, default=1)
#     progress = Column(Float, default=0.00)
#     last_viewed = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

# class Download(Base):
#     __tablename__ = "downloads"
    
#     download_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
#     user_id = Column(String(36), nullable=False)
#     song_id = Column(String(36), nullable=False)
#     file_name = Column(String(255), nullable=False)
#     file_format = Column(String(50), nullable=False)
#     itag = Column(String(50), nullable=False)
#     file_size = Column(BigInteger, nullable=False)
#     file_source = Column(String(50), nullable=False)
#     download_status = Column(Enum("SUCCESS", "FAILED", "IN_PROGRESS"), default="IN_PROGRESS")
#     user_agent = Column(Text)
#     timestamp = Column(TIMESTAMP, server_default=func.now())
#     retries = Column(Integer, default=0)
#     failure_reason = Column(Text)
#     is_partial = Column(Boolean, default=False)
#     thumbnail = Column(String(255), nullable=False)

# class InjustifyUser(Base):
#     __tablename__ = "injustifyusers"
    
#     email = Column(String(255), nullable=False, unique=True)
#     id = Column(String(36), primary_key=True)
#     name = Column(String(255), nullable=False)
#     picture = Column(String(855))
#     verified_email = Column(Boolean, default=False)
#     password = Column(String(255))
#     created_at = Column(TIMESTAMP, server_default=func.now())
#     updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
#     status = Column(Enum("active", "inactive", "suspended", "banned"), default="active")
#     last_login = Column(TIMESTAMP)
#     login_count = Column(Integer, default=0)
#     failed_login_attempts = Column(Integer, default=0)

# class InjustifyMusic(Base):
#     __tablename__ = "injustifymusic"
    
#     song_id = Column(String(10), primary_key=True)
#     title = Column(String(255), nullable=False, index=True)
#     artist = Column(String(255), nullable=False)
#     album = Column(String(255))
#     genre = Column(String(100))
#     release_date = Column(Date)
#     duration = Column(Float)
#     url = Column(String(500))
#     upload_date = Column(TIMESTAMP, server_default=func.now())
#     is_favorite = Column(Boolean, default=False)
#     views = Column(Integer, default=0)
#     dislike = Column(Integer)
#     thumbnail_path = Column(String(255))
#     is_explicit = Column(Boolean, default=False)
#     copyright_info = Column(String(255))
#     bpm = Column(Integer)

# class Playlist(Base):
#     __tablename__ = "playlists"
    
#     playlist_id = Column(String(10), primary_key=True)
#     name = Column(String(255), nullable=False)
#     description = Column(Text)
#     created_by = Column(String(36), nullable=False)
#     created_at = Column(TIMESTAMP, server_default=func.now())
#     updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
#     is_public = Column(Boolean, default=False)
#     cover_image = Column(String(255))
#     collaborative = Column(Boolean, default=False)
#     follower_count = Column(Integer, default=0)

# class PlaylistSong(Base):
#     __tablename__ = "playlistsongs"
    
#     playlist_song_id = Column(Integer, primary_key=True, autoincrement=True)
#     playlist_id = Column(String(10), nullable=False)
#     song_id = Column(String(10), nullable=False)
#     added_at = Column(TIMESTAMP, server_default=func.now())
#     added_by = Column(String(36))
#     position = Column(Integer)

# class VerificationSession(Base):
#     __tablename__ = "verification_sessions"
    
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     email = Column(String(255), nullable=False)
#     token = Column(String(255), nullable=False, unique=True)
#     expires_at = Column(TIMESTAMP, nullable=False)
#     verified_at = Column(TIMESTAMP)
#     purpose = Column(Enum('email_verification', 'password_reset', 'account_recovery'))

# # --------------------------
# # Security Utilities
# # --------------------------
# def verify_password(plain_password, hashed_password):
#     return pwd_context.verify(plain_password, hashed_password)

# def get_password_hash(password):
#     return pwd_context.hash(password)

# def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
#     to_encode = data.copy()
#     if expires_delta:
#         expire = datetime.utcnow() + expires_delta
#     else:
#         expire = datetime.utcnow() + timedelta(minutes=15)
#     to_encode.update({"exp": expire})
#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt

# async def get_current_admin(request: Request):
#     token = request.session.get("admin_token")
#     if not token:
#         raise HTTPException(status_code=401, detail="Not authenticated")
    
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         username: str = payload.get("sub")
#         if username is None:
#             raise HTTPException(status_code=401, detail="Invalid authentication credentials")
#     except JWTError:
#         raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
#     db = SessionLocal()
#     admin = db.query(AdminUser).filter(AdminUser.username == username).first()
#     db.close()
    
#     if admin is None:
#         raise HTTPException(status_code=401, detail="Admin user not found")
    
#     return admin

# # --------------------------
# # Admin Views
# # --------------------------
# class AdminUserView(ModelView, model=AdminUser):
#     column_list = ["id", "username", "email", "role", "is_active", "last_login"]
#     column_searchable_list = ["username", "email"]
#     column_filters = ["role", "is_active", "is_superadmin"]
#     form_columns = ["username", "email", "password_hash", "role", "is_active", "is_superadmin", "two_factor_enabled"]
#     column_sortable_list = ["id", "last_login", "created_at"]
#     column_default_sort = ("id", False)
    
#     async def on_model_change(self, data, model, is_created):
#         if is_created and "password_hash" in data:
#             model.password_hash = get_password_hash(data["password_hash"])
#         super().on_model_change(data, model, is_created)

# class AuditLogView(ModelView, model=AdminAuditLog):
#     column_list = ["id", "admin_id", "action", "entity_type", "created_at", "ip_address"]
#     column_searchable_list = ["action", "entity_type", "ip_address"]
#     column_filters = ["action", "entity_type"]
#     column_sortable_list = ["id", "created_at"]
#     column_default_sort = ("created_at", True)
#     can_create = False
#     can_edit = False
#     can_delete = False

# class InjustifyUserView(ModelView, model=InjustifyUser):
#     column_list = ["id", "email", "name", "status", "created_at", "last_login", "login_count"]
#     column_searchable_list = ["email", "name", "id"]
#     column_filters = ["status", "verified_email"]
#     form_excluded_columns = ["password"]
#     column_sortable_list = ["created_at", "last_login", "login_count"]
#     column_default_sort = ("created_at", True)
    
#     async def on_model_change(self, data, model, is_created):
#         if is_created:
#             logging.info(f"New user created: {model.email}")
#         super().on_model_change(data, model, is_created)

# # ... (similar enhanced views for all other models)

# # --------------------------
# # FastAPI App
# # --------------------------
# app = FastAPI(title="Injustify Admin Panel", 
#              description="Advanced administration interface for Injustify",
#              version="2.0")

# # Add session middleware for admin authentication
# app.add_middleware(SessionMiddleware, 
#                   secret_key=SECRET_KEY,
#                   session_cookie="admin_session",
#                   max_age=ADMIN_SESSION_TIMEOUT)

# # Admin panel setup with authentication
# admin = Admin(app, engine, 
#              base_url="/admin",
#              title="Injustify Admin",
#              logo_url="https://example.com/logo.png",
#              authentication_backend=get_current_admin)

# # Add all views to admin panel
# admin.add_view(AdminUserView)
# admin.add_view(AuditLogView)
# admin.add_view(InjustifyUserView)
# # ... (add all other views)

# # --------------------------
# # API Endpoints
# # --------------------------
# class AdminLogin(BaseModel):
#     username: str
#     password: str

# @app.post("/admin/login")
# async def admin_login(login: AdminLogin):
#     db = SessionLocal()
#     admin = db.query(AdminUser).filter(AdminUser.username == login.username).first()
#     db.close()
    
#     if not admin or not verify_password(login.password, admin.password_hash):
#         raise HTTPException(status_code=401, detail="Invalid credentials")
    
#     if not admin.is_active:
#         raise HTTPException(status_code=403, detail="Admin account disabled")
    
#     access_token = create_access_token(
#         data={"sub": admin.username},
#         expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     )
    
#     return {"access_token": access_token, "token_type": "bearer"}

# @app.get("/admin/me")
# async def read_admin_me(current_admin: AdminUser = Depends(get_current_admin)):
#     return {
#         "username": current_admin.username,
#         "email": current_admin.email,
#         "role": current_admin.role,
#         "is_superadmin": current_admin.is_superadmin
#     }

# # --------------------------
# # Main Execution
# # --------------------------
# if __name__ == "__main__":
#     # Create tables if they don't exist
#     Base.metadata.create_all(bind=engine)
    
#     # Set up logging
#     logging.basicConfig(
#         level=logging.INFO,
#         format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
#     )
    
#     # Run the application
#     uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)