import spotipy,json,os
from spotipy.oauth2 import SpotifyClientCredentials
client_id = os.getenv('SPOTIPY_CLIENT_ID')
client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id, client_secret))

def globalSearch_spotify(search):
    try:
        results = sp.search(q=search, type="track", limit=10)
        suggestions = [
            {"name": track['name'], "artist": track['artists'][0]['name']}
            for track in results['tracks']['items']
        ]
        return suggestions
    except Exception as e:
        print(f"Error in Spotify search: {str(e)}")
        return []


def search_songs_spotify(query):
    """Fetch Spotify search results for a given query."""
    try:
        #print("Searching Spotify... 🎶")

        results = sp.search(q=query, limit=10, type='track')
        #print(json.dumps(results,indent=4))
        songs = [
            {
                "title": track["name"],
                "artist": ", ".join([artist["name"] for artist in track["artists"]]),
                "url": track["external_urls"]["spotify"]
            }
            for track in results["tracks"]["items"]
        ]
        return songs
    except Exception as e:
        print(f"Error in search_songs_spotify: {str(e)}")
        return []


print(globalSearch_spotify('london town'))



