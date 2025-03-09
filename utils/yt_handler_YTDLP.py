import yt_dlp
import re
import requests
import asyncio
import threading
from queue import Queue
import urllib.parse
import aiohttp




async def fetch_streams(link):
    try:
        if not link:
            return {"success": False, "message": "No URL entered. Kindly enter a valid URL."}

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "simulate": True,
            "skip_download": True,
            "listformats": False,
            "socket_timeout": 10,
        }

        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(link, download=False))
            if not info:
                raise Exception("Failed to retrieve video information.")

        streams = await fetch_stream_details(info["formats"])
        
        return {
            "success": True,
            "streams": streams,
            "info": {
                "title": info.get("title"),
                "artist": info.get("uploader"),
                "description": info.get("description"),
                "views": info.get("view_count", 0),
            }
        }
    
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


async def fetch_stream_details(formats):
    async with aiohttp.ClientSession() as session:
        return await asyncio.gather(*(fetch_stream_info(session, f) for f in formats))


async def fetch_stream_info(session, f):
    return {
        "itag": f["format_id"],
        "ext": f["ext"],
        "resolution": f.get("resolution", "audio-only"),
        "video_codec": f.get("vcodec", "N/A"),
        "audio_codec": f.get("acodec", "N/A"),
        "vbr": f.get("vbr", 0),
        "abr": f.get("abr", 0),
        "size_mb": await get_file_size(session, f)
    }


async def get_file_size(session, stream):
    async def parse_clen_from_url(url):
        decoded_url = urllib.parse.unquote(url)
        clen_param = "clen="
        start_idx = decoded_url.find(clen_param)
        if start_idx == -1:
            return None

        start_idx += len(clen_param)
        end_idx = decoded_url.find(";", start_idx)
        if end_idx == -1:
            end_idx = len(decoded_url)

        clen_value = decoded_url[start_idx:end_idx]
        try:
            return int(clen_value)
        except ValueError:
            return None

    filesize = stream.get("filesize") or stream.get("filesize_approx")
    
    if filesize is None:
        url = stream.get("url")
        if not url:
            return None
        filesize = await parse_clen_from_url(url)
        if filesize is None:
            return None
    
    size_in_mb = filesize / (1024 * 1024)
    return round(size_in_mb, 3)






async def download_stream(url, itag, start_byte=0):
    """
    Asynchronously streams a YouTube video chunk by chunk using yt-dlp.
    """
    try:
        ydl_opts = {
            'format': itag,
            'noplaylist': True,
            'quiet': True,
        }

        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video_info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            video_url = next((fmt['url'] for fmt in video_info.get('formats', []) if fmt['format_id'] == itag), None)

            if not video_url:
                raise ValueError("Stream URL not found.")

        headers = {'Range': f'bytes={start_byte}-'}

        
        
        # Keep session open throughout
        session = aiohttp.ClientSession()
        stream = await session.get(video_url, headers=headers)
        stream.raise_for_status()

        async for chunk in stream.content.iter_any():  # ✅ Correct usage
            if not isinstance(chunk, (bytes, bytearray)):  
                chunk = str(chunk).encode()

            #print(f"Sending chunk of size {len(chunk)} bytes")  
            yield chunk
        
        await session.close()  # Close session after streaming completes
        
    except Exception as e:
        print(f"Error streaming video: {str(e)}")
        yield b"Error: " + str(e).encode()

