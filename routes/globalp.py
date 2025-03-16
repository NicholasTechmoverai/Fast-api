from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse


from utils.sp_handler import Search_suggestions_spotify
global_router = APIRouter()

