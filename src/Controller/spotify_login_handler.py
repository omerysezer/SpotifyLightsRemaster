from spotipy import Spotify, SpotifyOAuth, CacheFileHandler
import glob
from src.Files.credentials import SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, PERMISSION_SCOPE
import os
from glob import glob
import json

def remove_user_login():
    cache = glob('./src/Files/.cache*')
    if cache:
        os.remove(cache[0])

def login_user(code, state):
    cache_path = './src/Files/.cache-'
    cache_handler = CacheFileHandler(cache_path=cache_path)
    oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI, 
                        scope=PERMISSION_SCOPE, cache_handler=cache_handler, open_browser=False, state=state)
    oauth.get_access_token(code=code, check_cache=True)

    username = Spotify(auth_manager=oauth).me()['display_name']
    
    new_cache_path = cache_path + username
    os.rename(cache_path, new_cache_path)
    cache_handler = CacheFileHandler(cache_path=new_cache_path)
    oauth.cache_handler = cache_handler
    return oauth

def current_spotify_username():
    cache = get_spotify_cache_file()
    if not cache:
        return None
    
    # cache file is of form PATH/TO/FILE/.cache-USERNAME or PATH/TO/FILE/.cache-
    # in the second case there is one one element in cache.split which is PATH/TO/FILE/.cache
    cache_split = cache.split('-')
    if len(cache_split) < 2:
        return None
    return cache_split[1]

def get_spotify_cache_file():
    cache = glob('./src/Files/.cache*')
    if cache:
        return cache[0]
    
    return None

def get_auth_manager():
    cache_path = get_spotify_cache_file()
    if not cache_path:
        return None

    cache_handler = CacheFileHandler(cache_path=cache_path)
    oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI, cache_handler=cache_handler)
    return oauth

def user_is_logged_in():
    def logged_in():
        if current_spotify_username() is None:
            return False

        cache_path = get_spotify_cache_file()
        if not cache_path:
            return False
        try:
            oauth = get_auth_manager()
            with open(cache_path, 'r') as token_cache:
                token_info = json.load(token_cache)
                valid_token = oauth.validate_token(token_info)
                if valid_token:
                    return True
                else:
                    return False
        except:
            return False
        
    if not logged_in():
        remove_user_login()
        return False
    
    return True

