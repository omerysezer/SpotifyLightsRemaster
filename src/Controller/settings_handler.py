import json
import os

DEFAULT_SETTINGS = {
    "DEFAULT_BEHAVIOUR": "SPOTIFY_LIGHTS_ON",
    "PRIMARY_RGB": [
        255,
        255,
        255
    ],
    "SECONDARY_RGB": [
        0,
        0,
        0
    ],
    "STRIP_TYPE": None,
    'LED_COUNT': 0,
    "ANIMATIONS_LIST": [],
    "ANIMATION_DURATION": 10,
    "BRIGHTNESS": 50,
    "GIT_BRANCH": "master",
    "GIT_COMMIT_ID": "dd1490f"
}

class SettingsHandler():
    def __init__(self, path):
        self.settings_path = path

        if not os.path.exists(path):
            os.mknod(path)
            self._write_settings(DEFAULT_SETTINGS)
        else:
            settings = self._read_settings()
            for key in DEFAULT_SETTINGS.keys():
                if key not in settings:
                    settings[key] = DEFAULT_SETTINGS[key]
            self._write_settings(settings)
    
    def _read_settings(self):
        data = None
        with open(self.settings_path, 'r') as json_file:
            data = json.load(json_file)
        return data

    def _write_settings(self, data):
        if data is None:
            data = {}
        
        with open(self.settings_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)
        
    def update_primary_color(self, r, g, b):
        rgb_arr = [r, g, b]
        settings = self._read_settings()
        settings['PRIMARY_RGB'] = rgb_arr
        self._write_settings(settings)

    def get_primary_color(self):
        settings = self._read_settings()
        return tuple(settings['PRIMARY_RGB'])

    def update_secondary_color(self, r, g, b):
        rgb_arr = [r, g, b]
        settings = self._read_settings()
        settings['SECONDARY_RGB'] = rgb_arr
        self._write_settings(settings)

    def get_secondary_color(self):
        settings = self._read_settings()
        return tuple(settings['SECONDARY_RGB'])

    def update_git_branch(self, branch=None):
        settings = self._read_settings()
        settings['GIT_BRANCH'] = branch
        self._write_settings(settings)

    def get_git_branch(self):
        settings = self._read_settings()
        return tuple(settings['GIT_BRANCH'])
    
    def update_git_commit(self, commit=None):
        settings = self._read_settings()
        settings['GIT_COMMIT'] = commit
        self._write_settings(settings)

    def get_git_commit(self):
        settings = self._read_settings()
        return tuple(settings['GIT_COMMIT'])

    def update_default_behaviour(self, default_behaviour):
        if default_behaviour not in ['LIGHTS_OFF', 'SPOTIFY_LIGHTS_ON', 'ANIMATION_LIGHTS_ON']:
            raise Exception('Unsupported behaviour')
        
        settings = self._read_settings()
        settings['DEFAULT_BEHAVIOUR'] = default_behaviour
        self._write_settings(settings)

    def get_default_behaviour(self):
        settings = self._read_settings()
        return settings['DEFAULT_BEHAVIOUR']
    
    def update_enabled_animations(self, animation_names):
        settings = self._read_settings()
        settings['ANIMATIONS_LIST'] = animation_names or []
        self._write_settings(settings)

    def handle_deleted_animations(self, deleted_animations):
        if not deleted_animations:
            return
            
        settings = self._read_settings()
        settings['ANIMATIONS_LIST'] = [animation for animation in settings['ANIMATIONS_LIST'] if animation not in deleted_animations]
        print(settings['ANIMATIONS_LIST'])
        self._write_settings(settings)

    def get_animations(self):
        return self._read_settings()['ANIMATIONS_LIST']

    def update_animation_duration(self, duration):
        settings = self._read_settings()
        settings['ANIMATION_DURATION'] = duration
        self._write_settings(settings)
    
    def get_animation_duration(self):
        return self._read_settings()['ANIMATION_DURATION']
    
    def update_brightness(self, brightness):
        settings = self._read_settings()
        settings['BRIGHTNESS'] = brightness
        self._write_settings(settings)
        
    def get_brightness(self):
        return self._read_settings()['BRIGHTNESS']

    def get_strip_type(self):
        return self._read_settings()['STRIP_TYPE']

    def update_strip_type(self, strip_type):
        if strip_type not in ['dotstar', 'neopixel']:
            raise Exception('Unsupported strip type.')
        
        settings = self._read_settings()
        settings['STRIP_TYPE'] = strip_type
        self._write_settings(settings)
    
    def get_led_count(self):
        return self._read_settings()['LED_COUNT']
        
    def update_led_count(self, led_count):
        settings = self._read_settings()
        settings['LED_COUNT'] = led_count
        self._write_settings(settings)
        
    def reset_settings(self):
        self._write_settings(DEFAULT_SETTINGS)