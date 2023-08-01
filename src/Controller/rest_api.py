import spotipy
from spotipy.oauth2 import SpotifyOAuth
from src.Files.credentials import USERNAME, SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, AWS_ACCESS_KEY,\
    AWS_SECRET_KEY
import random, string
import os

permission_scopes = "user-modify-playback-state user-read-currently-playing user-read-playback-state"


from flask import Flask, redirect, request, send_from_directory, current_app, Response
import threading
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = './src/Animations/LightAnimations/'
ALLOWED_EXTENSIONS = {'py'}

class API:
    def __init__(self, communication_queue, kill_sentinel):
        self.communication_queue = communication_queue
        self.kill_sentinel = kill_sentinel # a dummy object which signals the class to kill the thread
    
    def _allowed_file(self, filename):
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
            elif data == "ANIMATION_LIGHTS_ON":
                self.communication_queue.put({'COMMAND': 'ANIMATION_LIGHTS_ON'})
            self.communication_queue.join()
            return 'Done'

        @app.route('/animation_files', methods=['GET', 'POST'])
        def upload_animation():
            if request.method == 'POST':
                # check if the post request has the file part
                if 'file' not in request.files:
                    print('test1')
                    return Response(status=400)
                file = request.files['file']
                # If the user does not select a file, the browser submits an
                # empty file without a filename.
                if file.filename == '':
                    # flash('No selected file')
                    print('test2')
                    return Response(status=400)
                if file and self._allowed_file(file.filename):
                    print('test3')
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    return Response(status=200)
                else:
                    return Response(status=500)
                
        app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
        # max content length = 16 megabytes
        app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000
        app.run(host='192.168.1.80', port=9090)
