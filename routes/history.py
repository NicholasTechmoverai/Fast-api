from fastapi import APIRouter

history_router = APIRouter()



@history_router.get("/{useremail}")
async def get_history(useremail: str):
    return {"history": []}
