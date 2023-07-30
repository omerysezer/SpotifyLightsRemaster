from src.Controller.settings_handler import SettingsHandler
from src.SpotifyLights.light_manager import manage
from src.Files.credentials import USERNAME, SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI
from spotipy.oauth2 import SpotifyOAuth
import threading
permission_scopes = "user-modify-playback-state user-read-currently-playing user-read-playback-state"

class Controller:
    def __init__(self):
        self.api_thread = None
        self.spotify_lights_thread = None
        self.settings_handler = SettingsHandler("./src/Files/settings.json")
        self.oauth_handler = SpotifyOAuth(username=USERNAME, client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI, 
                         scope=permission_scopes, cache_path=f"./src/Files/.cache-{USERNAME}", open_browser=False)

    def run(self):
        print(self.settings_handler.get_lights_on_after_startup())
        if self.settings_handler.get_lights_on_after_startup():
            self.api_thread = threading.Thread(target=manage, name="spotify_lights_thread", args=(False, self.settings_handler.get_base_color(), self.oauth_handler))
            self.api_thread.start()
            self.api_thread.join()
        else:
            while True:
                pass