import spotipy
from spotipy.oauth2 import SpotifyOAuth
from src.Files.credentials import USERNAME, SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, AWS_ACCESS_KEY,\
    AWS_SECRET_KEY
import random, string
import os
import threading
import zipfile
import shutil

permission_scopes = "user-modify-playback-state user-read-currently-playing user-read-playback-state"


from flask import Flask, redirect, request, send_from_directory, current_app, Response, render_template, send_file
import threading
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = './src/Animations/LightAnimations/'

class API:
    def __init__(self, communication_queue, kill_sentinel, settings_handler, settings_lock):
        self.communication_queue = communication_queue
        self.kill_sentinel = kill_sentinel # a dummy object which signals the class to kill the thread
        self.settings_handler = settings_handler
        self.settings_lock = settings_lock

    def _allowed_file(self, filename):
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ['py']

    def run(self):
        app = Flask(__name__)

        @app.route('/')
        def send_html():
            animation_files = os.listdir(UPLOAD_FOLDER)
            animation_files.sort(key=lambda file: os.path.getmtime(os.path.join(UPLOAD_FOLDER, file)))
            file_names = [name[:-3] for name in animation_files if self._allowed_file(name)]
            
            self.settings_lock.acquire()
            already_enabled_files = self.settings_handler.get_animations()
            self.settings_lock.release()
            
            return render_template("index.html", fileNames=file_names, enabledFiles=already_enabled_files)
            
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
                if request.form['action'] == 'upload':
                    # check if the post request has the file part
                    if 'file' not in request.files:
                        return Response(status=400)
                    file = request.files['file']
                    # If the user does not select a file, the browser submits an
                    # empty file without a filename.
                    if file.filename == '':
                        # flash('No selected file')
                        return Response(status=400)
                    if file and self._allowed_file(file.filename):
                        try:
                            filename = secure_filename(file.filename)
                            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                            return Response(status=200)
                        except:
                            return Response(status=500)
                    else:
                        return Response(status=500)
                elif request.form['action'] == 'select':
                    selected_animations = request.form.getlist('selected_files')
                    animation_durations = request.form.get('animation_time')
                    self.settings_lock.acquire()
                    self.settings_handler.update_enabled_animations(selected_animations)
                    self.settings_lock.release()
                    
                    return redirect('/')
                elif request.form['action'] == 'delete':
                    selected_animations = request.form.getlist('selected_files')
                    for animation in selected_animations:
                        path = os.path.join(UPLOAD_FOLDER, animation + '.py')
                        os.remove(path)
                    
                    self.settings_lock.acquire()
                    self.settings_handler.handle_deleted_animations(selected_animations)
                    self.settings_lock.release()

                    return redirect('/')
            elif request.method == 'GET':
                args = request.args
                if args.get('action') == 'download':
                    selected_animations = args.getlist('selected_files')
                    existing_animation_files = os.listdir(UPLOAD_FOLDER)

                    existing_animation_names = [name[:-3] for name in existing_animation_files if self._allowed_file(name)]

                    for animation in selected_animations:
                        if animation not in existing_animation_names:
                            raise Exception('File Not Found')
                    
                    zip_path = './src/Controller/temp_files/selected_animations.zip'
                    for file in os.path.listdir('./src/Controller/temp_files/'):
                        os.remove(file)
                        
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipped_folder:
                        for animation in selected_animations:
                            zipped_folder.write(UPLOAD_FOLDER + '/' + animation + '.py', arcname=animation + '.py')
                        zipped_folder.close()

                    # hack because send_file doesnt like absolute paths
                    zip_path = 'temp_files/selected_animations.zip'
                    return send_file(zip_path, mimetype='zip', download_name='animations.zip', as_attachment=True)
                else:
                    print('bye')
                    return Response(status=200)



        app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
        # max content length = 16 megabytes
        app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000
        app.run(host='192.168.1.80', port=9090)
