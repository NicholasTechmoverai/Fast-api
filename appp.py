import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from config import Config
from routes.main import main_router
from routes.profile import profile_router
from routes.downloads import router as downloads_router
from routes.notifications import notifications_router
from routes.globalp import global_router
from routes.history import history_router
from routes.songs import router as songs_router
from routes.stream import router as stream_router
from routes.download_streams import router as d_streams_router
from fastapi.staticfiles import StaticFiles
from socketio import AsyncServer
from socketio import ASGIApp
import socketio
from starlette.middleware.sessions import SessionMiddleware

FRONTEND_ORIGINS = [
    "http://192.168.100.2:8080",
    "http://192.168.100.2:5000",
    "http://127.0.0.1:5500",
    "http://localhost:5173"
]



media_directory = "static"
os.makedirs(media_directory, exist_ok=True)

from web_app import app, INJUserNamespace

app.add_middleware(SessionMiddleware, secret_key="0000")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)

sio_server = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*", 
    logger=False,
    engineio_logger=False
)
sio_app = socketio.ASGIApp(sio_server)

app.mount("/ws", sio_app)
sio_server.register_namespace(INJUserNamespace("/inj-user"))

app.mount("/static", StaticFiles(directory=media_directory), name="static")

app.include_router(main_router, prefix="")
app.include_router(profile_router, prefix="/api/profile")
app.include_router(downloads_router, prefix="/api")
app.include_router(notifications_router, prefix="/api/notifications")
app.include_router(global_router, prefix="/global")
app.include_router(history_router, prefix="/api/history")
app.include_router(songs_router, prefix="/api/songs")
app.include_router(stream_router, prefix="/api/stream")
app.include_router(d_streams_router, prefix="/api/download_streams")

if __name__ == "__main__":
    uvicorn.run("appp:app", host="192.168.100.2", port=5000, reload=True, log_level="info")
    #uvicorn.run("appp:app", host="127.0.0.1", port=5000, reload=True, log_level="info")





#uvicorn appp:app --reload --host 192.168.100.2 --port 5000
"""from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import os

app = FastAPI()

# Simulated image storage (using unique user IDs)
USER_IMAGES = {
    "184249562": "../static/uploads/user_102548979592530401204.png",
}

@app.get("/avatars/{user_id}")
def get_avatar(user_id: str, size: int = 400):
    # Fetch image path based on user ID
    image_path = USER_IMAGES.get(user_id)
    
    if not image_path or not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Avatar not found")
    
    # (Optional) Dynamically resize the image here if needed using Pillow
    # For simplicity, returning the original image
    return FileResponse(image_path, media_type="image/png")
"""