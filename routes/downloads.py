
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import mimetypes
from config import Config
from utils.yt_handler_YTDLP import download_stream,download_and_merge
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
    ext: str = 'mp4'

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
        ext = data.ext

        if not url or not itag or not filename:
            raise HTTPException(status_code=400, detail="songId, itag, and filename are required")

        dwnload_id = url

        if user_id:
            responce = await insert_download(
                user_id=user_id,
                song_id=song_id,
                file_name=filename,
                file_format=ext,
                itag=itag,
                file_size=file_size,
                file_source="youtube",
                thumbnail=thumbnail,
                user_agent=request.headers.get('User-Agent'),
                is_partial=(start_byte > 0),
            )

            if responce.get('download_id') and responce.get('download_id') is not None:
                dwnload_id = str(responce.get('download_id'))
               

        content_type, _ = mimetypes.guess_type(filename + ext)
        if not content_type:
            content_type = "video/mp4"

        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Accept-Ranges': 'bytes',
            'X-Download-URL': dwnload_id,
            'format': ext,
        }

        stream = (
            download_stream(url, itag, start_byte) 
            if itag in {'18', '140', '152'} 
            else download_and_merge(url, itag, '140')
        )

        return StreamingResponse(
            stream,
            media_type=content_type,
            headers=headers
        )

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))




