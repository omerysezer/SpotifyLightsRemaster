from src.Controller.settings_handler import SettingsHandler
from src.SpotifyLights.light_manager import manage
from src.Controller.rest_api import API
from src.Files.credentials import USERNAME, SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI
from spotipy.oauth2 import SpotifyOAuth
import threading
from queue import Queue
permission_scopes = "user-modify-playback-state user-read-currently-playing user-read-playback-state"

class Controller:
    def __init__(self):
        self.settings_handler = SettingsHandler("./src/Files/settings.json")
        self.oauth_handler = SpotifyOAuth(username=USERNAME, client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI, 
                         scope=permission_scopes, cache_path=f"./src/Files/.cache-{USERNAME}", open_browser=False)

        self.api_communicaton_queue = Queue()
        self.api_kill_sentinel = object()
        self.api = API(self.api_communicaton_queue, self.api_kill_sentinel)
        self.api_thread = None


        self.spotify_lights_thread = None
        self.controller_to_lights_queue = Queue() # a queue so the controller can pass messages to spotify lights manager thread
        self.light_to_controller_queue = Queue() # a queue so spotify lights manager thread can pass messages to controller
        self.spotify_lights_kill_sentinel = object()
        self.spotify_lights_are_on = False

    def run(self):
        self.api_thread = threading.Thread(target=self.api.run, name="rest_api_thread")
        self.api_thread.start()

        if self.settings_handler.get_lights_on_after_startup():
            self.spotify_lights_thread = threading.Thread(target=manage, name="spotify_lights_thread", args=(False, self.settings_handler.get_base_color(), 
                                                                                                  self.controller_to_lights_queue, self.light_to_controller_queue, self.spotify_lights_kill_sentinel))
            self.spotify_lights_thread.start()
            self.spotify_lights_are_on = True
        else:
            while True:
                pass
        
        while True:
            if not self.api_communicaton_queue.empty():
                command = self.api_communicaton_queue.get()
                if command['COMMAND'] == 'SWITCH_SPOTIFY_LIGHTS_ON_OFF':
                    print('CONTROLLER RECIEVED COMMAND... SENDING TO LIGHTS')
                    if self.spotify_lights_are_on:
                        self.controller_to_lights_queue.put(self.spotify_lights_kill_sentinel)
                        self.controller_to_lights_queue.join()
                        self.spotify_lights_thread.join()

                        self.controller_to_lights_queue = Queue() # clear the queues if there were any messages waiting
                        self.light_to_controller_queue = Queue()

                        self.spotify_lights_are_on = False
                    else:
                        self._create_spotify_lights_thread()
                        self.spotify_lights_thread.start()
                        self.spotify_lights_are_on = True
                    
                    print('CONTROLLER MARKING TASK AS DONE')
                    self.api_communicaton_queue.task_done()

    def _create_spotify_lights_thread(self):
        self.controller_to_lights_queue = Queue() # a queue so the controller can pass messages to spotify lights manager thread
        self.light_to_controller_queue = Queue() # a queue so spotify lights manager thread can pass messages to controller
        self.spotify_lights_thread = threading.Thread(target=manage, name="spotify_lights_thread", args=(False, self.settings_handler.get_base_color(), 
                                                                                                  self.controller_to_lights_queue, self.light_to_controller_queue, self.spotify_lights_kill_sentinel))