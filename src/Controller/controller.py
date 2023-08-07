from src.Controller.settings_handler import SettingsHandler
from src.SpotifyLights.light_manager import manage
from src.Controller.rest_api import API
from src.Files.credentials import USERNAME, SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, PERMISSION_SCOPE
from spotipy.oauth2 import SpotifyOAuth
from src.Animations.animation_controller import AnimationController
import threading
from queue import Queue
import json

class Controller:
    def __init__(self):
        self.settings_handler = SettingsHandler("./src/Files/settings.json")
        self.settings_lock = threading.Lock()
        self.oauth_handler = SpotifyOAuth(username=USERNAME, client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI, 
                         scope=PERMISSION_SCOPE, cache_path=f"./src/Files/.cache-{USERNAME}", open_browser=False)
        self.authenticated = False

        self.api_communicaton_queue = Queue()
        self.api_kill_sentinel = object()
        self.api = API(self.api_communicaton_queue, self.api_kill_sentinel, self.settings_handler, self.settings_lock)
        self.api_thread = None


        self.spotify_lights_thread = None
        self.controller_to_lights_queue = Queue() # a queue so the controller can pass messages to spotify lights manager thread
        self.light_to_controller_queue = Queue() # a queue so spotify lights manager thread can pass messages to controller
        self.spotify_lights_kill_sentinel = object()

        self.animation_controller = None
        self.animation_thread = None
        self.controller_to_animation_queue = Queue()
        self.animation_to_controller_queue = Queue()
        self.animation_kill_sentinel = object()

        self.current_command = None

    def _token_is_valid(self):
        try:
            with open(f"./src/Files/.cache-{USERNAME}", 'r') as token_cache:
                token_info = json.load(token_cache)
                valid_token = self.oauth_handler.validate_token(token_info)
                if valid_token:
                    return True
                else:
                    return False
        except:
            return False
        
    def run(self):
        self.authenticated = self._token_is_valid()
        
        self.api_thread = threading.Thread(target=self.api.run, name="rest_api_thread")
        self.api_thread.start()
        
        while True:
            self.authenticated = self._token_is_valid() # validate token to ensure connection to spotify is not lost
            if not self.api_communicaton_queue.empty():
                command = self.api_communicaton_queue.get()
                if command['COMMAND'] == 'LIGHTS_OFF':
                    if self._spotify_lights_are_running():
                        self._kill_spotify_lights()
                    if self._animation_is_running():
                        self._kill_animation_thread()

                if command['COMMAND'] == 'SPOTIFY_LIGHTS_ON':
                    if self._animation_is_running():
                        self._kill_animation_thread()
                    if not self._spotify_lights_are_running():
                        self._start_spotify_lights()

                if command['COMMAND'] == 'ANIMATION_LIGHTS_ON':
                    if self._spotify_lights_are_running():
                        self._kill_spotify_lights()
                    if not self._animation_is_running():
                        self._start_animation_thread()
                        print('starting animation')

                self.current_command = command['COMMAND']
                self.api_communicaton_queue.task_done()


            # default behaviour should only be triggered if there is no overriding command in self.current_command
            if not self.current_command:
                self.settings_lock.acquire()
                default_behaviour = self.settings_handler.get_default_behaviour() 
                self.settings_lock.release()

                if default_behaviour == "SPOTIFY_LIGHTS" and self.authenticated and not self._spotify_lights_are_running():
                    self._start_spotify_lights()
                elif default_behaviour == "ANIMATION" and not self._animation_is_running():
                    self._start_animation_thread()
                elif default_behaviour == "LIGHTS_OFF" and self._spotify_lights_are_running():
                    self._kill_spotify_lights()
                    self._kill_animation_thread()

        sleep(.1)

    def _start_spotify_lights(self):
        if self._spotify_lights_are_running():
            return
        
        self.settings_lock.acquire()
        base_color = self.settings_handler.get_base_color()
        self.settings_lock.release()

        self.controller_to_lights_queue = Queue() # a queue so the controller can pass messages to spotify lights manager thread
        self.light_to_controller_queue = Queue() # a queue so spotify lights manager thread can pass messages to controller
        self.spotify_lights_thread = threading.Thread(target=manage, name="spotify_lights_thread", args=(False, base_color, self.oauth_handler,
                                                                                                  self.controller_to_lights_queue, self.light_to_controller_queue, self.spotify_lights_kill_sentinel))
        self.spotify_lights_thread.start()

    def _kill_spotify_lights(self):
        if not self._spotify_lights_are_running():
            return

        self.controller_to_lights_queue.put(self.spotify_lights_kill_sentinel)
        self.controller_to_lights_queue.join() # wait for spotify lights to mark command as completed
        self.spotify_lights_thread.join() 

        self.controller_to_lights_queue = Queue() # clear the queues if there were any messages waiting
        self.light_to_controller_queue = Queue()

    def _spotify_lights_are_running(self):
        return self.spotify_lights_thread and self.spotify_lights_thread.is_alive()
            
    def _start_animation_thread(self):
        if self._animation_is_running():
            return
        
        self.controller_to_animation_queue = Queue()
        self.animation_to_controller_queue = Queue()
        self.animation_controller = AnimationController(None, 0, self.controller_to_animation_queue, 
                                                        self.animation_to_controller_queue, self.animation_kill_sentinel)
        self.animation_thread = threading.Thread(target=self.animation_controller.run, name="animation_thread")
        self.animation_thread.start()
        
    def _kill_animation_thread(self):
        if not self._animation_is_running():
            return

        self.controller_to_animation_queue.put(self.animation_kill_sentinel)
        self.animation_thread.join(timeout=10)

        if self._animation_is_running():
            raise Exception("Could Not Kill Animation Thread")
        
        self.animation_to_controller_queue = Queue()
        self.controller_to_animation_queue = Queue()
        
    def _animation_is_running(self):
        return self.animation_thread and self.animation_thread.is_alive() 
