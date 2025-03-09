from fastapi import APIRouter

notifications_router = APIRouter()

@notifications_router.get("/{useremail}")
async def get_notifications(useremail: str):
    return {"notifications": []}
