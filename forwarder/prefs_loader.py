import json
import os


class Preferences:
    initialized = False

    def __init__(self, prefs_full_path: str = '.' + os.sep + 'application.json'):
        if not self.initialized:
            self.initialized = True
            self._pref = None
            if os.path.exists(prefs_full_path) and os.path.isfile(prefs_full_path):
                with open(prefs_full_path, encoding='utf-8') as json_file:
                    self._prefs = json.load(json_file)
            else:
                raise ValueError('Error importing JSON preferences file.')

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_inst'):
            cls._inst = super(Preferences, cls).__new__(cls)
        return cls._inst

    def get_preferences(self):
        return self._prefs
