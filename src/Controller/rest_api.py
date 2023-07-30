import spotipy
from spotipy.oauth2 import SpotifyOAuth
from src.Files.credentials import USERNAME, SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, AWS_ACCESS_KEY,\
    AWS_SECRET_KEY
import random, string

permission_scopes = "user-modify-playback-state user-read-currently-playing user-read-playback-state"


from flask import Flask, redirect, request
import threading

app = Flask(__name__)

@app.route('/login')
def handle_spotify_auth_request():
    state = ''.join(random.choices(string.ascii_letters + string.digits, k = 16))
    auth_request = f'https://accounts.spotify.com/authorize?response_type=code&client_id={SPOTIPY_CLIENT_ID}&scope={permission_scopes}&redirect_uri={SPOTIPY_REDIRECT_URI}&state={state}'
    return redirect(auth_request)

@app.route('/')
def get_spotify_token_and_cache_it():
    args = request.args
    code = args.get('code')
    state = args.get('state')
    oauth = SpotifyOAuth(username=USERNAME, client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI, 
                         scope=permission_scopes, cache_path=f"./src/Files/.cache-{USERNAME}", open_browser=False, state=state)

    oauth.get_access_token(code=code, check_cache=True)
    return f"LOGGED IN!!!"

app.run(host='192.168.1.80', port=9090)
