import json
import os

DEFAULT_SETTINGS = {
    "DEFAULT_BEHAVIOUR": "SPOTIFY_LIGHTS",
    "BASE_RGB": [
        255,
        255,
        255
    ],
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
        
    def update_base_color(self, r=None, g=None, b=None):
        rgb_arr = [r, g, b]
        settings = self._read_settings()
        rgb_arr = [color if color is not None else settings['BASE_RGB'][i] for i, color in enumerate(rgb_arr)]
        settings['BASE_RGB'] = rgb_arr
        self._write_settings(settings)

    def get_base_color(self):
        settings = self._read_settings()
        return tuple(settings['BASE_RGB'])

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
        if default_behaviour not in ['LIGHTS_OFF', 'SPOTIFY_LIGHTS_ON', 'ANIMATIONS_ON']:
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

    def reset_settings(self):
        self._write_settings(DEFAULT_SETTINGS)