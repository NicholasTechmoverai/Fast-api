import os
import re
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from config import Config

router = APIRouter()

song_folder = Config.SONGS_FOLDER

@router.get("/{filename}")
async def stream_video(filename: str, request: Request):
    file_name = filename
    logging.error(f"Requested file: {file_name}")

    if not file_name:
        logging.error("File parameter is missing")
        raise HTTPException(status_code=400, detail="File parameter is required")

    file_path = os.path.join(song_folder, file_name)
    logging.info(f"Streaming file: {file_path}")

    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        raise HTTPException(status_code=404, detail="File not found")

    file_size = os.path.getsize(file_path)
    chunk_size = calculate_chunk_size(file_size)

    range_header = request.headers.get("range")
    if range_header:
        range_match = re.search(r"bytes=(\d+)-(\d*)", range_header)
        if not range_match:
            raise HTTPException(status_code=416, detail="Invalid Range header")
        
        start = int(range_match.group(1))
        end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
        
        if start >= file_size or end >= file_size:
            raise HTTPException(status_code=416, detail="Requested range not satisfiable")

        def range_stream():
            with open(file_path, "rb") as f:
                f.seek(start)
                yield f.read(end - start + 1)

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Content-Type": "video/mp4",
        }
        return StreamingResponse(range_stream(), status_code=206, headers=headers)
    
    def file_stream():
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                yield chunk
    
    return StreamingResponse(file_stream(), media_type="video/mp4")

def calculate_chunk_size(file_size):
    if file_size < 5 * 1024 * 1024:
        return 450 * 1024  # 450 KB
    elif file_size < 50 * 1024 * 1024:
        return 1 * 1024 * 1024  # 1 MB
    elif file_size < 200 * 1024 * 1024:
        return 2 * 1024 * 1024  # 2 MB
    else:
        return 5 * 1024 * 1024  # 5 MB

    

"""from flask import send_from_directory

@stream_bp.route('/<filename>')
def stream_video(filename):
    file_name = filename
    file_path = os.path.join(song_folder, file_name)

    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return Response("File not found", status=404)

    logging.info(f"Streaming file🛬🛬: {file_path}")

    return send_from_directory(song_folder, file_name, mimetype="video/mp4")
"""