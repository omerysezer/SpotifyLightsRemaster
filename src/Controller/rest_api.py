import spotipy
from spotipy.oauth2 import SpotifyOAuth
from src.Files.credentials import USERNAME, SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, AWS_ACCESS_KEY,\
    AWS_SECRET_KEY
import random, string

permission_scopes = "user-modify-playback-state user-read-currently-playing user-read-playback-state"


from flask import Flask, redirect, request, send_from_directory, current_app
import threading

class API:
    def __init__(self, communication_queue, kill_sentinel):
        self.communication_queue = communication_queue
        self.kill_sentinel = kill_sentinel # a dummy object which signals the class to kill the thread

    def run(self):
        app = Flask(__name__)

        @app.route('/')
        def send_html():
            return current_app.send_static_file("index.html")
            
        @app.route('/login')
        def handle_spotify_auth_request():
            state = ''.join(random.choices(string.ascii_letters + string.digits, k = 16))
            auth_request = f'https://accounts.spotify.com/authorize?response_type=code&client_id={SPOTIPY_CLIENT_ID}&scope={permission_scopes}&redirect_uri={SPOTIPY_REDIRECT_URI}&state={state}'
            return redirect(auth_request)

        @app.route('/spotifyredirect')
        def get_spotify_token_and_cache_it():
            args = request.args
            code = args.get('code')
            state = args.get('state')
            oauth = SpotifyOAuth(username=USERNAME, client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI, 
                                scope=permission_scopes, cache_path=f"./src/Files/.cache-{USERNAME}", open_browser=False, state=state)

            oauth.get_access_token(code=code, check_cache=True)
            return redirect("/")
        
        @app.route('/light_setting', methods=['POST'])
        def turn_off_lights():
            data = request.get_json()['light_setting']
            
            if data == "LIGHTS_OFF":
                self.communication_queue.put({'COMMAND': 'LIGHTS_OFF'})
            elif data == "SPOTIFY_LIGHTS_ON":
                self.communication_queue.put({'COMMAND': 'SPOTIFY_LIGHTS_ON'})

            self.communication_queue.join()
            return 'Done'


        app.run(host='192.168.1.80', port=9090)
