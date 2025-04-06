import os
import json
import random
import logging
import smtplib
import datetime as dl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from urllib.parse import urlencode

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse,Response
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config as StarletteConfig
from starlette.requests import Request
from starlette.responses import FileResponse

from google.oauth2 import id_token
from google.auth.transport import requests

from utils.userDb import validate_user_login, validate_user, create_new_user, fetch_user, update_user_password
from utils.auth_securityDb import set_token, validate_token
from utils.email_notification_sender import send_verify_link, send_codes
from config import Config

load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
MY_ID = os.getenv("MY_ID")
MY_SECRET = os.getenv("MY_SECRET")

if not MY_ID or not MY_SECRET:
    raise ValueError("Google OAuth credentials (MY_ID and MY_SECRET) must be set in the environment variables.")

# OAuth Configuration
oauth = OAuth(StarletteConfig())
google = oauth.register(
    name="google",
    client_id=MY_ID,
    client_secret=MY_SECRET,
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    access_token_url="https://oauth2.googleapis.com/token",
    client_kwargs={"scope": "openid email profile"},
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
)

main_router = APIRouter()



@main_router.get("/")
async def root():
    return {"message": "FastAPI is running"}

@main_router.post("/login")
async def login(request: Request):
    user_data = await request.json()
    useremail = user_data.get("email")
    password = user_data.get("password")
    
    if not useremail or not password:
        raise HTTPException(status_code=400, detail="Please provide both email and password")
    
    user = await validate_user_login(useremail, password)
    if user.get("userFound"):
        if user.get("truepassword"):
            data = user.get("user_info", {}).get('user_info')  
            return JSONResponse(content={"message": "Login successful","user" :  data}, status_code=200)
        
        raise HTTPException(status_code=401, detail="Invalid password. Please try again.")

    raise HTTPException(status_code=404, detail="User not found. Please check your email.")

@main_router.get("/login/google")
async def google_login(request: Request):  # Ensure request is passed
    redirect_uri = f"{Config.BACKEND_SERVER}/login/callback"
    return await google.authorize_redirect(request, redirect_uri)


@main_router.get("/login/callback")
async def authorize_route(request: Request):
    try:
        token = await google.authorize_access_token(request)

        if not token:
            raise HTTPException(status_code=400, detail="Google OAuth token is missing")

        user_info_response = await google.get("https://www.googleapis.com/oauth2/v1/userinfo", token=token)
        
        if user_info_response.status_code != 200:
            return RedirectResponse(url=f"{Config.FRONTEND_SERVER}/login?error=user_info_failed")
        
        user_info = user_info_response.json()
        
        user_email = user_info.get("email")
        if not user_email:
            return RedirectResponse(url=f"{Config.FRONTEND_SERVER}/login?error=email_missing")

        if not await validate_user(user_email):
            await create_new_user(user_info)

        user_data = await fetch_user(user_email)
        query_params = urlencode({
            "message": "Login successful",
            "user": json.dumps(user_data, default=str, ensure_ascii=False) 
        })

        return RedirectResponse(url=f"{Config.FRONTEND_SERVER}/?{query_params}")

    except Exception as e:
        logging.error(f"Authorization error: {e}")
        return RedirectResponse(url=f"{Config.FRONTEND_SERVER}/login?error=server_error")

@main_router.post("/verify-token")
async def verify_token(request: Request):
    data = await request.json()
    token = data.get("token")
    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            "507627163964-ms3hgtil3pe68bgsih6n6545t0lh2r91.apps.googleusercontent.com",
        )
        user_info = {"email": idinfo["email"], "name": idinfo.get("name", "Unknown"), "picture": idinfo.get("picture", "")}
        return JSONResponse(content={"success": True, "user": user_info})
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid token")

@main_router.post("/signup")
async def create_user(request: Request):
    data = await request.json()
    
    email = data.get("email")
    name = data.get("name")
    password = data.get("password")
    profile = data.get("picture", "/static/uploads/nouser.jpeg")
    
    if not email or not name or not password:
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")
    
    if await validate_user(email):
        raise HTTPException(status_code=400, detail="Email already exists. Please log in or reset your password.")
    
    result = await send_verify_link(email)
    if not result["success"]:
        raise HTTPException(status_code=500, detail="Failed to send verification email. Please try again later.")
    
    await create_new_user({
        "email": email,
        "name": name,
        "password": password,
        "picture": profile,
        "verified_email": False
    })
    
    return JSONResponse(content={"message": result["message"], "data": {"email": email, "name": name}}, status_code=200)

# More routes like password reset can be added following similar patterns
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

# Pydantic models for request validation
class EmailRequest(BaseModel):
    email: str

class VerifyCodeRequest(BaseModel):
    email: str
    code: str

class ResetPasswordRequest(BaseModel):
    email: str
    password: str
    code: str

# Simulated dependencies (replace with actual functions)
# Endpoint to send email reset codes
@main_router.post('/send_email_reset_codes')
async def send_email_reset_codes(request: EmailRequest):
    email = request.email

    response = await send_codes(email)

    if not response.get('success'):
        raise HTTPException(status_code=500, detail=response.get('message'))

    verification_code = response.get('codes')
    if not verification_code:
        raise HTTPException(status_code=500, detail="A valid token exists for this email. Check your inbox or wait 30 minutes.")

    token_response = await set_token(email, verification_code)

    if not token_response.get('success'):
        raise HTTPException(status_code=400, detail=token_response.get('message', 'A valid token already exists.'))

    return {"message": token_response.get('message', 'Token successfully sent!')}

# Endpoint to verify reset codes
@main_router.post('/verify_reset_codes')
async def verify_codes(request: VerifyCodeRequest):
    email, code = request.email, request.code

    print(f'🔍 Verifying EMAIL: {email}, CODES: {code}')

    try:
        check_token = await validate_token(email, code, False)

        if not check_token.get('valid'):
            raise HTTPException(status_code=400, detail=check_token.get('message'))

        return {"success": True}
    
    except Exception as e:
        print(f"⚠️ Error verifying code: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Endpoint to reset password
@main_router.post('/reset_email_password')
async def reset_password(request: ResetPasswordRequest):
    email, password, code = request.email, request.password, request.code

    check_token = await validate_token(email, code, True)
    if not check_token.get('valid'):
        print(f"Token validation failed for {email}: {check_token.get('message')}")
        raise HTTPException(status_code=400, detail=check_token.get('message'))

    update_password = await update_user_password(email, password)
    if not update_password.get('success'):
        print(f"Password update failed for {email}: {update_password.get('message')}")
        raise HTTPException(status_code=400, detail=update_password.get('message'))

    print(f"Password reset successful for {email}")
    return {"success": True}




BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_IMAGES = {
    "184249562": os.path.join(BASE_DIR, "../static/uploads/user_102548979592530401204.png"),
    "28895298": os.path.join(BASE_DIR, "../static/uploads/user_1a445842-2caf-4a7b-b7d0-7cc8b9afb1bd.png"),
    "102548980029997529247": os.path.join(BASE_DIR, "../static/uploads/user_116670681163950384994.png"),
    "102548979592530401204": os.path.join(BASE_DIR, "../static/uploads/user_94bc938e-7ea2-43b3-9818-146d1edd7446.png"),
    
}

@main_router.get("/avatars/{user_id}")
def get_avatar(user_id: str, size: int = 400):
    image_path = USER_IMAGES.get(user_id)

    if not image_path or not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail=f"Avatar not found, user_id:{user_id}, image_path:{image_path}")
    
    return FileResponse(image_path, media_type="image/png")