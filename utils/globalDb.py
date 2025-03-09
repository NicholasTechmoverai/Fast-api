import logging
import uuid
import mysql.connector
from config import Config
logging.basicConfig(level=logging.INFO)
from config import Config
import aiomysql



async def update_view_count(songId, userId, songPercentage):
    """
    Async function to update the view count for a song effectively.
    """
    #print(f"Updating view count for song {songId} by user {userId} with progress {songPercentage}")
    
    try:
        conn = await Config.get_db_connection()
        if not conn:
            return {"success": False, "message": "Database connection failed"}

        async with conn.cursor() as cursor:
            sql_check = "SELECT id, view_count, progress FROM views WHERE song_id = %s AND user_id = %s"
            await cursor.execute(sql_check, (songId, userId))
            existing_view = await cursor.fetchone()

            if existing_view:
                view_id, view_count, last_progress = existing_view

                if last_progress >= 98 and songPercentage < 10:
                    # Reset progress for a fresh playthrough
                    sql_reset_progress = """
                        UPDATE views 
                        SET progress = %s, last_viewed = NOW()
                        WHERE song_id = %s AND user_id = %s
                    """
                    await cursor.execute(sql_reset_progress, (songPercentage, songId, userId))

                elif last_progress < 50 and songPercentage >= 50:
                    # Increment view count if crossing 50% in a new session
                    sql_update_view = """
                        UPDATE views 
                        SET progress = %s, view_count = view_count + 1, last_viewed = NOW()
                        WHERE song_id = %s AND user_id = %s
                    """
                    await cursor.execute(sql_update_view, (songPercentage, songId, userId))

                else:
                    # Just update progress
                    sql_update_progress = """
                        UPDATE views 
                        SET progress = %s, last_viewed = NOW()
                        WHERE song_id = %s AND user_id = %s
                    """
                    await cursor.execute(sql_update_progress, (songPercentage, songId, userId))

            else:
                # First-time entry: insert new record
                viewCount = 1 if songPercentage >= 50 else 0
                sql_insert = """
                    INSERT INTO views (user_id, song_id, view_count, progress) 
                    VALUES (%s, %s, %s, %s)
                """
                await cursor.execute(sql_insert, (userId, songId, viewCount, songPercentage))

            await conn.commit()
            return {"success": True, "message": "View count updated successfully"}

    except Exception as err:
        print(f"Error updating view count: {err}")
        return {"success": False, "message": str(err)}

    finally:
        if conn:
            Config.pool.release(conn)  # ✅ Release connection instead of closing


async def insert_download(user_id, song_id, file_name, file_format, itag, file_size, file_source, thumbnail, user_agent=None, is_partial=False):
    """Async function to insert a new download into the database."""
    try:
        conn = await Config.get_db_connection()
        if not conn:
            return {"success": False, "message": "Database connection failed"}

        async with conn.cursor() as cursor:
            query = """
                INSERT INTO downloads (user_id, song_id, file_name, file_format, itag, file_size, file_source, thumbnail, user_agent, is_partial) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (user_id, song_id, file_name, file_format, itag, file_size, file_source, thumbnail, user_agent, is_partial)
            await cursor.execute(query, values)
            await conn.commit()

            return {"success": True, "download_id": cursor.lastrowid}

    except Exception as e:
        print(f"Error inserting download: {e}")
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            Config.pool.release(conn)  # ✅ Release connection instead of closing


async def fetch_songs(user_id=None, songs_per_page=15, offset=0, search=None, songId=None):
    """Async function to fetch songs from the database."""
    try:
        conn = await Config.get_db_connection()
        if not conn:
            return {"success": False, "message": "Database connection failed"}

        async with conn.cursor() as cursor:
            base_query = """
                SELECT 
                    injustifyMusic.song_id, 
                    artist, 
                    title, 
                    url, 
                    thumbnail_path, 
                    duration, 
                    views, 
                    upload_date,
                    (SELECT COUNT(*) FROM songlikes WHERE songlikes.song_id = injustifyMusic.song_id) AS likes,
                    EXISTS(
                        SELECT 1 
                        FROM songlikes 
                        WHERE songlikes.song_id = injustifyMusic.song_id AND songlikes.user_id = %s
                    ) AS liked
                FROM injustifyMusic
            """
            values = [user_id] if user_id else [None]

            if not search or search.lower() == 'null' and not songId:
                count_query = "SELECT COUNT(*) FROM injustifyMusic"
                await cursor.execute(count_query)
                total_songs = (await cursor.fetchone())[0]

                if offset >= total_songs:
                    return {"message": "No results found"}

                sql_query = f"{base_query} ORDER BY title LIMIT %s OFFSET %s"
                values.extend([songs_per_page, offset])
                await cursor.execute(sql_query, tuple(values))

            elif songId and not search:
                sql_query = f"{base_query} WHERE song_id = %s ORDER BY title LIMIT %s OFFSET %s"
                values.extend([songId, songs_per_page, offset])
                await cursor.execute(sql_query, tuple(values))

            else:
                count_query = """
                    SELECT COUNT(*)
                    FROM injustifyMusic
                    WHERE title LIKE %s OR artist LIKE %s
                """
                search_filter = f"%{search}%"
                await cursor.execute(count_query, (search_filter, search_filter))
                total_songs = (await cursor.fetchone())[0]

                if offset >= total_songs:
                    return {"message": "No results found"}

                sql_query = f"""
                    {base_query}
                    WHERE title LIKE %s OR artist LIKE %s
                    ORDER BY title LIMIT %s OFFSET %s
                """
                values.extend([search_filter, search_filter, songs_per_page, offset])
                await cursor.execute(sql_query, tuple(values))

            songs = await cursor.fetchall()
            result = [
                {
                    "song_id": song[0],
                    "artist": song[1],
                    "title": song[2],
                    "url": f'{song[3]}',
                    "thumbnail": f"{Config.thumbnailPath}/{song[4]}",
                    "duration": song[5],
                    "views": song[6],
                    "date": song[7].strftime('%Y-%m-%d %H:%M:%S'),
                    "likes": song[8],
                    "liked": bool(song[9]),  
                    "Stype": "local"
                }
                for song in songs
            ]

            return {"total_songs": total_songs, "songs": result}

    except Exception as e:
        return {"message": "Error fetching songs", "error": str(e)}

    finally:
        if conn:
            Config.pool.release(conn)  # ✅ Release connection instead of closing


async def get_playlistSongs(playlistId):
    """Async function to fetch songs from a playlist."""
    sql_query = """
        SELECT ps.song_id, im.title, im.artist, im.url, im.thumbnail_path, p.name 
        FROM playlistSongs ps 
        JOIN injustifyMusic im ON ps.song_id = im.song_id 
        JOIN playlists p ON ps.playlist_id = p.playlist_id 
        WHERE ps.playlist_id = %s;
    """
    try:
        conn = await Config.get_db_connection()
        if not conn:
            return {"success": False, "message": "Database connection failed"}

        async with conn.cursor() as cursor:
            await cursor.execute(sql_query, (playlistId,))
            songs = await cursor.fetchall()

        if not songs:
            return {"playlist_name": None, "songs": []}

        playlist_name = songs[0][5]

        result = [
            {
                "song_id": song[0],
                "title": song[1],
                "artist": song[2],
                "url": f'{song[3]}',
                "thumbnail": f"{Config.thumbnailPath}/{song[4]}",
                "Stype": "local"
            }
            for song in songs
        ]

        return {"playlist_name": playlist_name, "playlistId": playlistId, "songs": result}

    except Exception as e:
        return {"message": "Error fetching playlist songs", "error": str(e)}

    finally:
        if conn:
            Config.pool.release(conn)  # ✅ Release connection instead of closing


async def fetchTrendingSongs():
    """
    Fetch trending songs based on views, likes, and comments within the last 30 days.

    Criteria: JUST FOR DEVELOPMENT
    - Songs viewed by at least 5 unique users in the past 30 days.
    - Songs with at least 5 comments in the past 30 days.
    - Songs with engagement ranked by:
      1. Average progress percentage.
      2. Number of likes.
      3. Number of comments.
    """
    print("Fetching trending songs...")

    sql_query = """
        SELECT 
            s.song_id, 
            s.title, 
            s.artist, 
            s.thumbnail_path,
            s.upload_date, 
            AVG(v.progress) AS average_progress,
            COUNT(DISTINCT l.user_id) AS likes_count,
            COUNT(DISTINCT c.comment_id) AS comments_count
        FROM injustifymusic s
        JOIN views v ON s.song_id = v.song_id
        LEFT JOIN songlikes l ON s.song_id = l.song_id AND l.like_date >= DATE_SUB(NOW(), INTERVAL 1 MONTH)
        LEFT JOIN comments c ON s.song_id = c.songId AND c.created_at >= DATE_SUB(NOW(), INTERVAL 1 MONTH)
        WHERE v.last_viewed >= DATE_SUB(NOW(), INTERVAL 1 MONTH)
        GROUP BY s.song_id, s.title, s.artist, s.thumbnail_path, s.upload_date
        HAVING COUNT(DISTINCT v.user_id) >= 1 AND COUNT(DISTINCT c.comment_id) >= 1
        ORDER BY average_progress DESC, likes_count DESC, comments_count DESC
    """

    try:
        # 🔹 Get DB connection (Replace with your actual connection logic)
        conn = await Config.get_db_connection()
        if not conn:
            return {"success": False, "message": "Database connection failed"}

        async with conn.cursor() as cursor:
            await cursor.execute(sql_query)  # ✅ Await query execution
            trending_songs = await cursor.fetchall()  # ✅ Await fetching results

        # 🔹 Process results
        trending_songs_list = [
            {
                'id': song[0],
                'title': song[1],
                'artist': song[2],
                'thumbnail': f"{Config.thumbnailPath}/{song[3]}",
                'upload_date': song[4].strftime('%Y-%m-%d'),
                'average_progress': song[5],
                'likes_count': song[6],
                'comments_count': song[7]
            }
            for song in trending_songs
        ]

        return {"success": True, "feed": trending_songs_list}

    except Exception as e:
        print(f"Error fetching trending songs: {e}")
        return {"success": False, "message": "An error occurred while fetching trending songs"}

    finally:
        if conn:
            Config.pool.release(conn)  # ✅ Release connection instead of closing

async def fetch_User_LikedSongs(userId, offset=0, limit=10):
    """
    Fetch songs liked by a user, sorted in descending order (recently liked),
    with pagination (10 per fetch by default). Converts tuples to dictionaries.
    """
    print(f"Fetching liked songs for user: {userId}")

    sql_query = """
        SELECT 
            s.song_id, 
            s.title, 
            s.artist, 
            s.thumbnail_path AS album_cover, 
            s.release_date, 
            l.like_date
        FROM injustifymusic s
        JOIN songlikes l ON s.song_id = l.song_id
        WHERE l.user_id = %s
        ORDER BY l.like_date DESC
        LIMIT %s OFFSET %s
    """
    values = (userId, limit, offset)

    try:
        conn = await Config.get_db_connection()  # ✅ Get async connection
        async with conn.cursor() as cursor:
            await cursor.execute(sql_query, values)
            liked_songs = await cursor.fetchall()

        liked_songs_list = [
            {
                "song_id": song[0],
                "title": song[1],
                "artist": song[2],
                "thumbnail": f'{Config.thumbnailPath}/{song[3]}',  # ✅ Fixed path separator
                "release_date": song[4].strftime('%Y-%m-%d') if song[4] else None,
                "like_date": song[5].strftime('%Y-%m-%d %H:%M:%S') if song[5] else None
            }
            for song in liked_songs
        ]

        return {"success": True, "feed": liked_songs_list}

    except aiomysql.MySQLError as err:
        print(f"Error fetching liked songs: {err}")
        return {"success": False, "message": "Failed to fetch liked songs!"}

    finally:
        if conn:
            Config.pool.release(conn)  # ✅ Release connection instead of closing


async def fetchUserTopSongs(userId, limit=10):
    """
    Fetch top songs based on how many times a specific user has viewed them.
    """
    print(f"Fetching top songs for user: {userId}")

    sql_query = """
        SELECT 
            s.song_id, 
            s.title, 
            s.artist, 
            s.thumbnail_path AS album_cover, 
            s.release_date,
            v.view_count AS user_view_count
        FROM injustifymusic s
        JOIN views v ON s.song_id = v.song_id
        WHERE v.user_id = %s
        ORDER BY v.view_count DESC
        LIMIT %s
    """
    values = (userId, limit)

    try:
        conn = await Config.get_db_connection()  
        async with conn.cursor() as cursor:
            await cursor.execute(sql_query, values)
            top_songs = await cursor.fetchall()

        top_songs_list = [
            {
                "song_id": song[0],
                "title": song[1],
                "artist": song[2],
                "thumbnail": f'{Config.thumbnailPath}/{song[3]}',  
                "release_date": song[4].strftime('%Y-%m-%d') if song[4] else None,
                "user_view_count": song[5]
            }
            for song in top_songs
        ]

        return {"success": True, "feed": top_songs_list}

    except aiomysql.MySQLError as err:
        print(f"Error fetching top songs: {err}")
        return {"success": False, "message": "Failed to fetch top songs!"}

    finally:
        if conn:
            Config.pool.release(conn)  # ✅ Release connection instead of closing


async def fetchStreamRate(userId):
    """
    Fetch stream rate for 10 users surrounding the given userId, including user info.
    Prevents negative ranking issues.
    """
    print(f"Fetching stream rate for user: {userId}")

    try:
        # ✅ Await the connection since it's an async function
        conn = await Config.get_db_connection()  
        if not conn:
            return {"success": False, "message": "Database connection failed"}

        sql_query = """
            WITH user_activity AS (
                SELECT 
                    v.user_id,
                    COUNT(*) AS total_views,
                    COUNT(DISTINCT v.song_id) AS unique_songs,
                    AVG(v.progress) AS avg_completion,
                    SUM(v.view_count) AS total_view_count,
                    MAX(v.last_viewed) AS last_active
                FROM injustify.views v
                GROUP BY v.user_id
            ), ranking_data AS (
                SELECT 
                    ua.user_id,
                    ua.total_views,
                    ua.unique_songs,
                    ua.avg_completion,
                    ua.total_view_count,
                    DATEDIFF(NOW(), ua.last_active) AS days_since_active,
                    (ua.total_view_count * 0.5 + ua.unique_songs * 0.3 + ua.avg_completion * 0.2) 
                    / (1 + DATEDIFF(NOW(), ua.last_active) * 0.05) AS engagement_score
                FROM user_activity ua
            ), ranked_users AS (
                SELECT 
                    rd.user_id, 
                    u.name,
                    u.picture,
                    RANK() OVER (ORDER BY rd.engagement_score DESC) AS global_rank,
                    rd.engagement_score,
                    rd.total_views,
                    rd.unique_songs,
                    rd.avg_completion
                FROM ranking_data rd
                JOIN injustify.injustifyusers u ON rd.user_id = u.id
            ), user_position AS (
                SELECT global_rank FROM ranked_users WHERE user_id = %s
            )
            SELECT * FROM ranked_users 
            WHERE global_rank BETWEEN 
                CASE 
                    WHEN (SELECT global_rank FROM user_position) > 5 
                    THEN (SELECT global_rank FROM user_position) - 5 
                    ELSE 1  -- If user is in the top 5, start from rank 1
                END
            AND 
                CASE 
                    WHEN (SELECT global_rank FROM user_position) > 5 
                    THEN (SELECT global_rank FROM user_position) + 5 
                    ELSE (SELECT global_rank FROM user_position) + (5 + (5 - (SELECT global_rank FROM user_position))) 
                    -- This ensures we get 10 users in total by shifting the upper bound higher
                END
            ORDER BY global_rank;
        """

        async with conn.cursor() as cursor:
            await cursor.execute(sql_query, (userId,))  # ✅ Await execute
            stream_rate = await cursor.fetchall()  # ✅ Await fetchall

        if stream_rate:
            return {
                "success": True,
                "stream_rate": [
                    {
                        "userId": row[0],
                        "username": row[1],
                        "profile_image_url": f"{Config.profilePath}/{row[2]}",
                        "global_rank": row[3],
                        "engagement_score": row[4],
                        "total_views": row[5],
                        "unique_songs": row[6],
                        "avg_completion": row[7]
                    }
                    for row in stream_rate
                ]
            }
        
        return {"success": True, "stream_rate": []}

    except Exception as e:
        print(f"Error fetching stream rate: {e}")
        return {"success": False, "message": "An error occurred while fetching stream rate"}

    finally:
        if conn:
            Config.pool.release(conn) 


async def createPlaylistDB(playlistName, userId):
    print(f"Creating playlist {playlistName} with user {userId}")
    playlist_id = f"pl{str(uuid.uuid4())[:8]}"
    sql_query = "INSERT INTO playlists (playlist_id, name, created_by) VALUES (%s, %s, %s)"
    values = (playlist_id, playlistName, userId)

    conn = None
    try:
        conn = await Config.get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute(sql_query, values)
            await conn.commit()
            return {
                "success": True,
                "message": "Playlist created successfully 😊",
                "info": {
                    "id": playlist_id,
                    "playlistName": playlistName,
                    "created_by": userId,
                    "type": "local"
                }
            }
    except Exception as err:
        print(f"Error creating playlist: {err}")
        return {"success": False, "message": "Error creating playlist!!"}
    finally:
        if conn:
            Config.pool.release(conn)  # ✅ Release connection instead of closing


async def updatePlaylistDB(playlistId, songId, action, newPlaylistName=None):
    print(f"Updating playlist {playlistId}, songId: {songId}, action: {action}, newPlaylistName: {newPlaylistName}")
    
    try:
        conn = await Config.get_db_connection()
        async with conn.cursor() as cursor:
            if action == "add":
                sql_query = "INSERT INTO playlistSongs (playlist_id, song_id) VALUES (%s, %s)"
                await cursor.execute(sql_query, (playlistId, songId))
            
            elif action == "remove":
                sql_query = "DELETE FROM playlistSongs WHERE playlist_id = %s AND song_id = %s"
                await cursor.execute(sql_query, (playlistId, songId))
            
            elif action == "delete":
                await cursor.execute("DELETE FROM playlistSongs WHERE playlist_id = %s", (playlistId,))
                await cursor.execute("DELETE FROM playlists WHERE playlist_id = %s", (playlistId,))
            
            elif action == "rename" and newPlaylistName:
                sql_query = "UPDATE playlists SET name = %s WHERE playlist_id = %s"
                await cursor.execute(sql_query, (newPlaylistName, playlistId))
            
            await conn.commit()
            return {"success": True, "message": f"Playlist {action} successfully!"}
    
    except Exception as err:
        print(f"Error updating playlist: {err}")
        return {"success": False, "message": f"Failed to {action} playlist!"}
    
    finally:
        Config.pool.release(conn)  # ✅ Release connection instead of closing


async def get_playlists(user_id):
    if not user_id:
        return {"success": False, "message": "User ID is required"}

    try:
        conn = await Config.get_db_connection()
        async with conn.cursor() as cursor:
            sql_query = """
                SELECT p.playlist_id, p.name, p.description, p.created_by, p.created_at, u.Picture,
                    (SELECT COUNT(*) FROM playlistSongs WHERE playlist_id = p.playlist_id) AS song_count
                FROM playlists p
                LEFT JOIN injustifyusers u ON p.created_by = u.id
                WHERE p.created_by = %s
            """
            await cursor.execute(sql_query, (user_id,))
            playlists = await cursor.fetchall()

        if playlists:
            return {
                "success": True,
                "playlists": [
                    {
                        "id": p[0], "name": p[1], "description": p[2], "created_by": p[3],
                        "created_at": p[4].strftime('%Y-%m-%d %H:%M:%S'), "picture": f"{Config.profilePath}/{p[5]}",
                        "song_count": p[6]
                    }
                    for p in playlists
                ]
            }
        return {"success": False, "message": "No playlists found for this user", "playlists": []}

    except Exception as err:
        print(f"Database Error: {err}")
        return {"success": False, "message": "An error occurred while fetching playlists", "error": str(err)}
    
    finally:
        Config.pool.release(conn)  # ✅ Release connection instead of closing
