from fastapi import APIRouter, HTTPException
from config import Config
from utils.userDb import fetch_user, fetch_downloads
from fastapi import FastAPI, UploadFile, Form, File, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional

from utils.userDb import update_UserProfile

profile_router = APIRouter()

@profile_router.get("/{useremail}")
async def get_profile(useremail: str):
    print(f"GET request for user profile: {useremail}")
    result = await fetch_user(useremail)  
    user_info = result.get("user_info", {}) 
    if not user_info:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_info": user_info}

@profile_router.get("/downloads/{useremail}")
async def get_downloads(useremail: str):
    print(f"Getting downloads for {useremail}")
    result = await fetch_downloads(useremail, None, None, None, None, None, 'timestamp ASC')
    downloads = result.get('downloads', [])
    return {"downloads": downloads}



@profile_router.get("/updateProfile")
async def update_profile(
    userId: str = Form(...),
    email: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    profilePic: Optional[UploadFile] = File(None)
):
    try:
        if not userId:
            return JSONResponse(content={"success": False, "message": "You need to log in!"})

        print("Updating profile....")
        result = update_UserProfile(userId, name, email, password, profilePic)

        if result.get('success'):
            return JSONResponse(content={"success": True, "message": "Profile updated successfully."})
        else:
            return JSONResponse(content={"success": False, "message": "Failed to update profile."})

    except Exception as e:
        return JSONResponse(content={"success": False, "message": "An error occurred", "error": str(e)})
