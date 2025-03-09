from fastapi import APIRouter, HTTPException
from config import Config
from utils.userDb import fetch_user, fetch_downloads

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
