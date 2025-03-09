from fastapi import APIRouter, HTTPException, Query
from config import Config
import mysql.connector
import threading
from pydantic import BaseModel
from typing import Dict, Any

from utils.sp_handler import search_songs_spotify
from utils.yt_handler_PYTUBE import search_videos_yt
from utils.globalDb import (
    fetch_songs, get_playlistSongs, fetch_User_LikedSongs, fetchTrendingSongs,
    fetchUserTopSongs, get_playlists, fetchStreamRate,createPlaylistDB,updatePlaylistDB
)

router = APIRouter()

mydb = Config.mydb
mycursor = mydb.cursor()

youtube_results = {}
spotify_results = {}
yt_lock = threading.Lock()
sp_lock = threading.Lock()

@router.get("/gp/{userId}")
async def fetch_user_top_songs(userId: str, limit: int = 10):
    """
    Fetch top songs based on how many times a specific user has viewed them.
    """
    print(f"Fetching top songs for user: {userId}")
    
    useridentity = "user_id" if "@" not in userId else "email"

    try:
        sql_query = f"""
            SELECT 
                s.song_id, s.title, s.artist, s.thumbnail_path AS album_cover, 
                s.release_date, v.view_count AS user_view_count
            FROM injustifymusic s
            JOIN views v ON s.song_id = v.song_id
            WHERE v.{useridentity} = %s
            ORDER BY v.view_count DESC
            LIMIT %s
        """
        values = (userId, limit)
        mycursor.execute(sql_query, values)
        top_songs = mycursor.fetchall()

        top_songs_list = [
            {
                "song_id": song[0],
                "title": song[1],
                "artist": song[2],
                "thumbnail": f"/{song[3]}",
                "release_date": song[4].strftime('%Y-%m-%d') if song[4] else None,
                "user_view_count": song[5]
            }
            for song in top_songs
        ]

        return {"success": True, "songs": top_songs_list}

    except mysql.connector.Error as err:
        print(f"Error fetching top songs: {err}")
        raise HTTPException(status_code=500, detail="Failed to fetch top songs")

@router.get("/{user_id}")
async def return_fetch_songs(user_id: str, search: str = Query(None, alias="search")):
    if search and search.lower() != "null":
        threading.Thread(target=fetch_youtube_results, args=(search,), daemon=True).start()
        threading.Thread(target=fetch_spotify_results, args=(search,), daemon=True).start()
    return await fetch_songs(user_id, 24, 0, search, None)

def fetch_youtube_results(query):
    results = search_videos_yt(query)
    with yt_lock:
        youtube_results[query] = results

def fetch_spotify_results(query):
    results = search_songs_spotify(query)
    with sp_lock:
        spotify_results[query] = results

@router.get("/pol/yt/{userId}")
async def get_yt_results(userId: str, search: str = Query(None, alias="search")):
    with yt_lock:
        if search in youtube_results:
            return {"success": True, "songs": youtube_results[search]}
    raise HTTPException(status_code=404, detail="YouTube results not ready yet")

@router.get("/pol/sp/{userId}")
async def get_sp_results(userId: str, search: str = Query(None, alias="search")):
    with sp_lock:
        if search in spotify_results:
            return {"success": True, "songs": spotify_results[search]}
    raise HTTPException(status_code=404, detail="Spotify results not ready yet")

@router.get("/song/info/{songId}")
async def fetch_song_info(songId: str):
    return fetch_songs(None, 24, 24, 0, songId)

@router.get("/pl/{pl_id}")
async def fetch_playlists(pl_id: str):
    if not pl_id:
        raise HTTPException(status_code=400, detail="Playlist ID is required")
    
    pl_songs = await get_playlistSongs(pl_id)
    if not pl_songs:
        raise HTTPException(status_code=204, detail="Playlist is empty")
    
    return {"songs": pl_songs}

@router.get("/yls/{userId}")
async def get_user_liked_songs(userId: str):
    if not userId:
        raise HTTPException(status_code=400, detail="User ID is required")
        
    liked_songs = await fetch_User_LikedSongs(userId, 0, 20)  

    if not liked_songs or not liked_songs.get("feed"):
        raise HTTPException(status_code=204, detail="No liked songs found")
    
    return {"songs": liked_songs.get("feed")}

@router.get("/utr/{userId}")
async def get_user_top_songs(userId: str):
    if not userId:
        raise HTTPException(status_code=400, detail="User ID is required")
        
    songs = await fetchUserTopSongs(userId, 20)
    if not songs:
        raise HTTPException(status_code=204, detail="No liked songs found")
    
    return {"songs": songs.get("feed")}

@router.get("/tr")
async def get_trending_songs():
    songs = await  fetchTrendingSongs()
    if not songs:
        raise HTTPException(status_code=204, detail="No trending songs found")
    
    return {"songs": songs.get("feed")}

@router.get("/pls/{userId}")
async def get_user_playlists(userId: str):
    if not userId:
        raise HTTPException(status_code=400, detail="User ID is required")
    
    playlists = await get_playlists(userId)
    if not playlists:
        raise HTTPException(status_code=204, detail="No playlists found")
    
    return {"playlists": playlists.get("playlists")}

class PlaylistCreateRequest(BaseModel):
    name: str
    userId: str

class PlaylistRenameRequest(BaseModel):
    playlistId: str
    newName: str

class PlaylistDeleteRequest(BaseModel):
    playlistId: str

@router.get("/str/{userId}")
async def get_stream_position(userId: str):
    if not userId:
        raise HTTPException(status_code=400, detail="User ID is required")
    
    rate = await fetchStreamRate(userId)
    if not rate:
        raise HTTPException(status_code=204, detail="No stream position found")
    
    return {"stream_rate": rate.get("stream_rate")}

@router.post("/add_pls")
async def create_playlist(request: PlaylistCreateRequest):
    if not request.name:
        raise HTTPException(status_code=400, detail="Playlist name cannot be empty")
    
    result = await createPlaylistDB(request.name, request.userId)
    if result.get("success"):
        return {"success": True, "message": result["message"], "info": result["info"]}
    
    raise HTTPException(status_code=500, detail=result["message"])

@router.post("/rnm_pls")
async def rename_playlist(request: PlaylistRenameRequest):
    if not request.newName or not request.playlistId:
        raise HTTPException(status_code=400, detail="Playlist ID and new name are required")
    
    result = await updatePlaylistDB(request.playlistId, None, "rename", request.newName)
    if result.get("success"):
        return {"success": True, "message": result["message"], "info": result.get("info", {})}
    
    raise HTTPException(status_code=500, detail=result.get("message", "Unknown error"))

@router.post("/del_pls")
async def delete_playlist(request: PlaylistDeleteRequest):
    if not request.playlistId:
        raise HTTPException(status_code=400, detail="Playlist ID is required")
    
    result = await updatePlaylistDB(request.playlistId, None, "delete")
    if result.get("success"):
        return {"success": True, "message": result["message"], "info": result.get("info", {})}
    
    raise HTTPException(status_code=500, detail=result.get("message", "Unknown error"))











from datetime import datetime

def calculate_stream_position(view_history):
    """
    Determines the next song position based on viewing history.
    
    :param view_history: List of dictionaries containing song data
        [{'song_id': 1, 'view_count': 5, 'progress': 80, 'last_viewed': '2025-02-20 14:30:00'}, ...]
    :return: song_id of the next song
    """
    weights = {
        'view_count': 0.5,   # Weight for the number of views
        'progress': 0.3,     # Weight for progress percentage
        'recency': 0.2       # Weight for recency of last view
    }
    
    def time_decay(last_viewed):
        """Calculates time decay factor (more recent = higher value)."""
        now = datetime.now()
        last_viewed_dt = datetime.strptime(last_viewed, '%Y-%m-%d %H:%M:%S')
        delta_days = (now - last_viewed_dt).days + 1  # Avoid division by zero
        return 1 / delta_days  # More recent = higher value
    
    for song in view_history:
        song['recency'] = time_decay(song['last_viewed'])
        song['score'] = (song['view_count'] * weights['view_count'] +
                         song['progress'] * weights['progress'] / 100 +
                         song['recency'] * weights['recency'])
    
    # Sort by score in descending order and return top song_id
    next_song = max(view_history, key=lambda x: x['score'])
    return next_song['song_id']
    































"""
WITH user_activity AS (
    SELECT 
        user_id,
        COUNT(*) AS total_views,
        COUNT(DISTINCT song_id) AS unique_songs,
        AVG(progress) AS avg_completion,
        SUM(view_count) AS total_view_count,
        MAX(last_viewed) AS last_active
    FROM injustify.views
    GROUP BY user_id
), ranking_data AS (
    SELECT 
        user_id,
        total_views,
        unique_songs,
        avg_completion,
        total_view_count,
        -- Apply time decay for recent activity boost
        DATEDIFF(NOW(), last_active) AS days_since_active,
        -- Scoring system
        (total_view_count * 0.5 + unique_songs * 0.3 + avg_completion * 0.2) / (1 + DATEDIFF(NOW(), last_active) * 0.05) AS engagement_score
    FROM user_activity
)
SELECT user_id, 
       RANK() OVER (ORDER BY engagement_score DESC) AS global_rank,
       engagement_score,
       total_views,
       unique_songs,
       avg_completion
FROM ranking_data;

"""    





