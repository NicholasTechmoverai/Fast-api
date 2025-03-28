from fastapi import FastAPI
from fastapi_admin.app import app as admin_app
from fastapi_admin.providers.login import UsernamePasswordProvider
from fastapi_admin.resources import Link
from models import Admin
import  os
import redis.asyncio as redis
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 🔹 FIXED: Removed `enable_captcha=True`
login_provider = UsernamePasswordProvider(
    admin_model=Admin,
    login_logo_url="https://preview.tabler.io/static/logo.svg"
)

app = FastAPI()

# 🔹 FIXED: Corrected @admin_app.register instead of @app.register
@admin_app.register
class Home(Link):
    label = "Injust"
    icon = "fas fa-home"
    url = "/admin"

redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

@app.on_event("startup")
async def startup():
    # 🔹 FIXED: Corrected Redis connection
    admin_app.configure(
        logo_url="https://preview.tabler.io/static/logo-white.svg",
        template_folders=[os.path.join(BASE_DIR, "templates")],
        providers=[login_provider],
        redis=redis_client,
    )

app.mount("/admin", admin_app)
