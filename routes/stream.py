import os
import re
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from config import Config
import mimetypes

router = APIRouter()

song_folder = Config.SONGS_FOLDER

# @router.get("/{filename}")
# async def stream_video(filename: str, request: Request):
#     file_name = filename
#     logging.error(f"Requested file: {file_name}")

#     if not file_name:
#         logging.error("File parameter is missing")
#         raise HTTPException(status_code=400, detail="File parameter is required")

#     file_path = os.path.join(song_folder, file_name)
#     logging.info(f"Streaming file: {file_path}")

#     if not os.path.exists(file_path):
#         logging.error(f"File not found: {file_path}")
#         raise HTTPException(status_code=404, detail="File not found")

#     file_size = os.path.getsize(file_path)
#     chunk_size = calculate_chunk_size(file_size)

#     range_header = request.headers.get("range")
#     if range_header:
#         range_match = re.search(r"bytes=(\d+)-(\d*)", range_header)
#         if not range_match:
#             raise HTTPException(status_code=416, detail="Invalid Range header")
        
#         start = int(range_match.group(1))
#         end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
        
#         if start >= file_size or end >= file_size:
#             raise HTTPException(status_code=416, detail="Requested range not satisfiable")

#         def range_stream():
#             with open(file_path, "rb") as f:
#                 f.seek(start)
#                 yield f.read(end - start + 1)

#         headers = {
#             "Content-Range": f"bytes {start}-{end}/{file_size}",
#             "Accept-Ranges": "bytes",
#             "Content-Length": str(end - start + 1),
#             "Content-Type": "video/mp4",
#         }
#         return StreamingResponse(range_stream(), status_code=206, headers=headers)
    
#     def file_stream():
#         with open(file_path, "rb") as f:
#             while chunk := f.read(chunk_size):
#                 yield chunk
    
#     return StreamingResponse(file_stream(), media_type="video/mp4")



from typing import Optional
from mimetypes import guess_type


# Configuration
CHUNK_SIZE = (1024 * 1024 )/2 # 1MB chunks by default
MAX_CHUNK_SIZE = 10 * 1024 * 1024  # 10MB maximum chunk size
MIN_CHUNK_SIZE = 512 * 1024  # 512KB minimum chunk size
DEFAULT_MEDIA_TYPE = "application/octet-stream"

def calculate_chunk_size(file_size: int) -> int:
    """Calculate optimal chunk size based on file size"""
    if file_size <= 10 * 1024 * 1024:  # <= 10MB
        return max(MIN_CHUNK_SIZE, file_size // 10)
    elif file_size <= 100 * 1024 * 1024:  # <= 100MB
        return 2 * 1024 * 1024  # 2MB
    else:
        return min(MAX_CHUNK_SIZE, file_size // 50)

def get_media_type(filename: str) -> str:
    """Get media type based on file extension"""
    guessed_type = guess_type(filename)[0]
    return guessed_type if guessed_type else DEFAULT_MEDIA_TYPE

def parse_range_header(range_header: str, file_size: int) -> tuple[int, int]:
    """Parse range header and validate the requested range"""
    range_match = re.search(r"bytes=(\d+)-(\d*)", range_header)
    if not range_match:
        raise HTTPException(status_code=416, detail="Invalid Range header")
    
    start = int(range_match.group(1))
    end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
    
    # Validate range
    if start >= file_size or end >= file_size or start > end:
        raise HTTPException(status_code=416, detail="Requested range not satisfiable")
    
    return start, end

def generate_chunks(file_path: str, start: int = 0, end: Optional[int] = None, chunk_size: int = CHUNK_SIZE):
    """Generator function to stream file in chunks"""
    with open(file_path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1 if end is not None else None
        
        while True:
            if remaining is not None and remaining <= 0:
                break
                
            bytes_to_read = chunk_size
            if remaining is not None and bytes_to_read > remaining:
                bytes_to_read = remaining
                
            chunk = f.read(bytes_to_read)
            if not chunk:
                break
                
            yield chunk
            
            if remaining is not None:
                remaining -= len(chunk)

@router.get("/{filename}")
async def stream_file(filename: str, request: Request):
    file_path = os.path.join(song_folder, filename)
    logging.info(f"Requested file: {file_path}")

    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        raise HTTPException(status_code=404, detail="File not found")

    file_size = os.path.getsize(file_path)
    chunk_size = calculate_chunk_size(file_size)
    media_type = get_media_type(filename)
    range_header = request.headers.get("range")

    if range_header:
        try:
            start, end = parse_range_header(range_header, file_size)
            
            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(end - start + 1),
                "Content-Type": media_type,
            }
            
            return StreamingResponse(
                generate_chunks(file_path, start, end, chunk_size),
                status_code=206,
                headers=headers,
                media_type=media_type
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Full file response
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Content-Type": media_type,
    }
    
    return StreamingResponse(
        generate_chunks(file_path, chunk_size=chunk_size),
        headers=headers,
        media_type=media_type
    )

    

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