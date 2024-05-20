from setting import Setting

class setting_keywords:

    def __init__(self):
        self.setting = Setting()

    def update_setting(self, key, value):
        self.setting.update_setting(key, value)

    def set_backupstore(self):
        self.setting.set_backupstore()

    def reset_backupstore(self):
        self.setting.reset_backupstore()
