from setting import Setting


class setting_keywords:

    def __init__(self):
        self.setting = Setting()

    def update_setting(self, key, value, retry=True):
        self.setting.update_setting(key, value, retry)

    def get_setting(self, key):
        return self.setting.get_setting(key)

    def reset_settings(self):
        self.setting.reset_settings()
