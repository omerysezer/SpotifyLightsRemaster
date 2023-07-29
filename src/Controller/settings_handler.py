import json
import os

DEFAULT_SETTINGS = {
    'BASE_RGB': (255, 255, 255),
    'GIT_BRANCH': 'master',
    'GIT_COMMIT_ID': 'dd1490f'
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

    def reset_settings(self):
        self._write_settings(DEFAULT_SETTINGS)