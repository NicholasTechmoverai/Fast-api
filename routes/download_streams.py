import math
import os
import mimetypes
import asyncio
from fastapi import APIRouter, Request, Depends,HTTPException
from fastapi.responses import JSONResponse
from ffmpeg import probe
from config import Config
from utils.yt_handler_YTDLP import fetch_streams

router = APIRouter()
download_folder = Config.SONGS_FOLDER

@router.get("/injustify/{filename}")
def get_streams_local(filename: str):
    file_path = os.path.join(download_folder, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found in storage.")
    
    file_size_bytes = os.path.getsize(file_path)
    file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
    mime_type, _ = mimetypes.guess_type(file_path)
    filename_without_extension = '.'.join(filename.split('.')[:-1])
    
    metadata = {
        "title": filename_without_extension,
        "type": mime_type or "unknown",
        "size_mb": file_size_mb,
        "success": True,
        "info": {
            "title": filename_without_extension,
            "artist": filename,
            "description": "",
            "views": ""
        }
    }
    
    if mime_type and ("video" in mime_type or "audio" in mime_type):
        try:
            media_info = probe(file_path)
            streams = media_info.get("streams", [])
            video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
            audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

            if video_stream:
                metadata.update({
                    "resolution": f"{video_stream.get('width', 0)}x{video_stream.get('height', 0)}",
                    "video_codec": video_stream.get("codec_name", "unknown"),
                    "width": int(video_stream.get("width", 0)),
                    "height": int(video_stream.get("height", 0)),
                    "vbr": math.ceil(int(video_stream.get("bit_rate", 0)) / 1000) if video_stream.get("bit_rate") else 0,
                })

            if audio_stream:
                metadata.update({
                    "audio_codec": audio_stream.get("codec_name", "unknown"),
                    "abr": math.ceil(int(audio_stream.get("bit_rate", 0)) / 1000) if audio_stream.get("bit_rate") else 0,
                })

            duration = float(media_info.get("format", {}).get("duration", 0))
            metadata["duration"] = round(duration, 2)
        
        except Exception as e:
            metadata.update({"error": f"Failed to extract media info: {str(e)}"})
    
    return JSONResponse(content=[metadata] * 3)




@router.post("/youtube")
async def get_streams(request: Request):
    try:
        data = await request.json()
        link = data.get("songId")
        
        if not link:
            raise HTTPException(status_code=400, detail="No link provided. Please provide a valid YouTube link.")
        
        streams = await fetch_streams(link)
        
        if streams.get("success"):
            return JSONResponse(content={
                "success": True,
                "streams": streams.get("streams"),
                "info": streams.get("info"),
                "link": link,
                "msg": streams.get("help_msg"),
                "msg_type": streams.get("msg_type", "HELP"),
            })
        
        raise HTTPException(status_code=500, detail=streams.get("message", "Unable to fetch streams."))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


