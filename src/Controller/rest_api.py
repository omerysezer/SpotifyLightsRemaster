import spotipy
from spotipy.oauth2 import SpotifyOAuth, CacheFileHandler
from src.Files.credentials import SPOTIPY_CLIENT_ID, SPOTIPY_REDIRECT_URI
import random, string
import os
import zipfile
import shutil
from glob import glob
from src.Controller.spotify_login_handler import remove_user_login, login_user, current_spotify_username, user_is_logged_in

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

        self.behavior_lock = threading.Lock()
        self.timed_out_lock = threading.Lock()
        self.current_behaviour = self.settings_handler.get_default_behaviour()
        self.spotify_lights_timed_out = False

    def _allowed_file(self, filename):
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ['py']
    
    def notify_spotify_lights_timed_out(self):
        self.settings_lock.acquire()
        self.behavior_lock.acquire()
        self.timed_out_lock.acquire()
        self.current_behaviour = self.settings_handler.get_default_behaviour()
        self.spotify_lights_timed_out = True
        self.timed_out_lock.release()
        self.behavior_lock.release()
        self.settings_lock.release()

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
            primary_color = self.settings_handler.get_primary_color()
            secondary_color = self.settings_handler.get_secondary_color()
            led_strip_type = self.settings_handler.get_strip_type()
            led_count = self.settings_handler.get_led_count()
            self.settings_lock.release()

            self.behavior_lock.acquire()
            current_behaviour = self.current_behaviour
            self.behavior_lock.release()
            
            self.timed_out_lock.acquire()
            timed_out = self.spotify_lights_timed_out
            self.timed_out_lock.release()

            username = None if not user_is_logged_in() else current_spotify_username()

            if not led_strip_type:
                return render_template("setup.html")

            curr_file = None
            prev_file = None 
            next_file = None
            if current_behaviour == 'ANIMATION_LIGHTS_ON' and len(already_enabled_files) > 1: 
                idx_holder = {'GET_ANIMATION_IDX': None}
                self.communication_queue.put(idx_holder)
                self.communication_queue.join()
                animation_index = idx_holder['GET_ANIMATION_IDX']
                prev_file = already_enabled_files[(animation_index - 1) % len(already_enabled_files)]
                next_file = already_enabled_files[(animation_index + 1) % len(already_enabled_files)]
                curr_file = already_enabled_files[animation_index]

                if len(already_enabled_files) == 2:
                    prev_file = None

            return render_template("index.html", fileNames=file_names, enabledFiles=already_enabled_files, duration=animation_duration, 
                                   brightness=brightness, default_light_setting=default_behaviour, current_behaviour=self.current_behaviour, 
                                   primary_color=primary_color, secondary_color=secondary_color, username=username, spotify_lights_timed_out=self.spotify_lights_timed_out,
                                   strip_type=led_strip_type, led_count=led_count, curr_file=curr_file, prev_file=prev_file, next_file=next_file)

        @app.route('/login', methods=['GET'])
        def login():
            state = ''.join(random.choices(string.ascii_letters + string.digits, k = 16))
            auth_request = f'https://accounts.spotify.com/authorize?response_type=code&client_id={SPOTIPY_CLIENT_ID}&scope={permission_scopes}&redirect_uri={SPOTIPY_REDIRECT_URI}&state={state}'
            return redirect(auth_request)

        @app.route('/logout', methods=['GET'])
        def logout():
            self.communication_queue.put({'LOGGED_OUT'}) # kill lights before touching spotify authentication stuff to prevent errors
            self.communication_queue.join()
            remove_user_login()
            return redirect("/")

        @app.route('/spotifyredirect', methods=['GET'])
        def get_spotify_token_and_cache_it():
            args = request.args
            code = args.get('code')
            state = args.get('state')
            oauth = login_user(code, state)
            self.communication_queue.put({'LOGGED_IN'})
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
                if setting == 'SPOTIFY_LIGHTS_ON':
                    self.timed_out_lock.acquire()
                    self.spotify_lights_timed_out = False
                    self.timed_out_lock.release()

                self.communication_queue.put({'COMMAND': setting})
                self.communication_queue.join()

                self.behavior_lock.acquire()
                self.current_behaviour = setting
                self.behavior_lock.release()
            return redirect("/")

        @app.route('/brightness', methods=['POST'])
        def update_brightness():
            brightness = int(request.get_json()['brightness'])
            self.settings_lock.acquire()
            self.settings_handler.update_brightness(brightness)
            self.settings_lock.release()

            self.communication_queue.put({'BRIGHTNESS': brightness})
            return Response(status=200)

        @app.route('/strip', methods=['POST'])
        def update_strip_type():
            strip_type = request.form.get('strip_type')
            num_led = int(request.form.get('led_count'))
            try:
                self.settings_handler.update_strip_type(strip_type)
            except:
                return f'Strip type: {strip_type} is unsupported.', 400
            
            self.settings_handler.update_led_count(num_led)
            self.communication_queue.put({'UPDATE_STRIP_TYPE': {'NUM_LED': num_led, 'STRIP_TYPE': strip_type}})
            self.communication_queue.join()
            return redirect("/")

        @app.route('/colors', methods=['POST'])
        def update_base_color():
            def hex_to_rgb(hex):
                hex = hex[1:] # remove leading #

                r = int(hex[:2], 16)
                g= int(hex[2:4], 16)
                b = int(hex[4:6], 16)

                return (r, g, b)

            primary_color_hex_str = request.form.get('primary_color') 
            secondary_color_hex_str = request.form.get('secondary_color') 
            primary_color = hex_to_rgb(primary_color_hex_str)
            secondary_color = hex_to_rgb(secondary_color_hex_str)

            self.settings_lock.acquire()
            # * unpacks tuple into argument list
            self.settings_handler.update_primary_color(*primary_color)
            self.settings_handler.update_secondary_color(*secondary_color)
            self.settings_lock.release()

            self.communication_queue.put({'SPOTIFY_COLORS': [primary_color, secondary_color]})
            self.communication_queue.join()
            return redirect('/')

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
                            os.execl(sys.executable, sys.executable, *sys.argv)
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
                    
                    self.communication_queue.put({'ANIMATION_SETTINGS_UPDATED'})
                    self.communication_queue.join()
                    
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

                    if not existing_animation_names:
                        return "NO_FILES_AVAILABLE", 400
                    
                    if not selected_animations:
                        return "NO_FILE_SELECTED", 400

                    for animation in selected_animations:
                        if animation not in existing_animation_names:
                            return f"FILE_NOT_FOUND: {animation}", 500

                    zip_path = './src/Controller/temp_files/selected_animations.zip'                    
                    if os.path.exists(zip_path):
                        os.remove(zip_path)

                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipped_folder:
                        for animation in selected_animations:
                            zipped_folder.write(UPLOAD_FOLDER + '/' + animation + '.py', arcname=animation + '.py')
                        zipped_folder.close()

                    # does not use zip_path because send_file doesnt like absolute paths
                    zip_path_not_absolute = 'temp_files/selected_animations.zip'
                    return send_file(zip_path_not_absolute, mimetype='zip', download_name='animations.zip', as_attachment=True)
                else:
                    return Response(status=200)

        @app.route('/next_animation', methods=['GET'])
        def skip_animation():
            self.communication_queue.put({'NEXT_ANIMATION'})
            self.communication_queue.join()
            return redirect("/")

        @app.route('/prev_animation', methods=['GET'])
        def go_to_prev_animation():
            self.communication_queue.put({'PREV_ANIMATION'})
            self.communication_queue.join()
            return redirect("/")
        
        app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
        # max content length = 16 megabytes
        app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000
        app.run(host='localhost', port=9090)
