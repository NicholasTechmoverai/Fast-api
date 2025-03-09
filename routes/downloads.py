from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import mimetypes
from config import Config
from utils.yt_handler_YTDLP import download_stream
from utils.globalDb import insert_download

router = APIRouter()
mydb = Config.mydb
mycursor = mydb.cursor()

class DownloadRequest(BaseModel):
    song_url: str
    songId: str
    itag: str
    filename: str
    start_byte: int = 0
    userId: str = None
    size_mb: float = None
    thumbnailUrl: str = None

@router.post("/download/yt")
async def download_video(request: Request, data: DownloadRequest):
    print("Processing download request...")
    
    try:
        url = data.song_url
        song_id = data.songId
        itag = data.itag
        filename = data.filename
        start_byte = data.start_byte
        user_id = data.userId
        file_size = data.size_mb
        thumbnail = data.thumbnailUrl

        if not url or not itag or not filename:
            raise HTTPException(status_code=400, detail="songId, itag, and filename are required")

        if user_id:
            await insert_download(
                user_id=user_id,
                song_id=song_id,
                file_name=filename,
                file_format=itag,
                itag=itag,
                file_size=file_size,
                file_source="youtube",
                thumbnail=thumbnail,
                user_agent=request.headers.get('User-Agent'),
                is_partial=(start_byte > 0),
            )

        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            content_type = "video/mp4"

        return StreamingResponse(
            download_stream(url, itag, start_byte),
            media_type=content_type,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Accept-Ranges': 'bytes',
                'X-Download-URL': url,
            }
        )
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

