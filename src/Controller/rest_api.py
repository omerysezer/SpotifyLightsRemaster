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

        self.current_behaviour = self.settings_handler.get_default_behaviour()

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
            animation_duration = self.settings_handler.get_animation_duration()
            brightness = self.settings_handler.get_brightness()
            already_enabled_files = self.settings_handler.get_animations()
            default_behaviour = self.settings_handler.get_default_behaviour()
            self.settings_lock.release()
            
            return render_template("index.html", fileNames=file_names, enabledFiles=already_enabled_files, duration=animation_duration, 
                                    brightness=brightness, default_light_setting=default_behaviour, current_behaviour=self.current_behaviour)
            
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
        def light_setting():
            setting = request.form.get('light_setting')
            make_setting_default = request.form.get('light_setting_cb')
            if make_setting_default:
                self.settings_lock.acquire()
                self.settings_handler.update_default_behaviour(setting)
                self.settings_lock.release()
            else:
                self.communication_queue.put({'COMMAND': setting})
                self.communication_queue.join()
                self.current_behaviour = setting

            return redirect("/")

        @app.route('/brightness', methods=['POST'])
        def update_brightness():
            brightness = int(request.get_json()['brightness'])
            self.settings_lock.acquire()
            self.settings_handler.update_brightness(brightness)
            self.settings_lock.release()

            self.communication_queue.put({'BRIGHTNESS': brightness})
            return Response(status=200)

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
                    animation_duration = round(float(request.form.get('animation_duration')), 2)

                    if animation_duration.is_integer():
                        animation_duration = int(animation_duration)

                    self.settings_lock.acquire()
                    self.settings_handler.update_enabled_animations(selected_animations)
                    self.settings_handler.update_animation_duration(animation_duration)
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
                elif request.form['action'] == 'set_duration':
                    duration = request.form.get('duration')
                    self.settings_lock.acquire()
                    self.settings_handler.update_animation_duration(duration)
                    self.settings_lock.release()

                    return redirect('/')
            elif request.method == 'GET':
                args = request.args
                if args.get('action') == 'download':
                    selected_animations = args.getlist('selected_files')
                    existing_animation_files = os.listdir(UPLOAD_FOLDER)
                    existing_animation_names = [name[:-3] for name in existing_animation_files if self._allowed_file(name)]

    
                    print("exisitng: ", selected_animations)
                    if not existing_animation_names:
                        return "NO_FILES_AVAILABLE", 400
                    
                    if not selected_animations:
                        return "NO_FILE_SELECTED", 400

                    for animation in selected_animations:
                        if animation not in existing_animation_names:
                            return f"FILE_NOT_FOUND: {animation}", 500
                    
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipped_folder:
                        for animation in selected_animations:
                            zipped_folder.write(UPLOAD_FOLDER + '/' + animation + '.py', arcname=animation + '.py')
                        zipped_folder.close()

                    # hack because send_file doesnt like absolute paths
                    zip_path = 'temp_files/selected_animations.zip'
                    return send_file(zip_path, mimetype='zip', download_name='animations.zip', as_attachment=True)
                else:
                    return Response(status=200)



        app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
        # max content length = 16 megabytes
        app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000
        app.run(host='192.168.1.80', port=9090)
