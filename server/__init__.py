from ayon_server.addons import BaseServerAddon
from .settings import ToastNotifySettings, DEFAULT_TOASTNOTIFY_SETTINGS

class ToastNotify(BaseServerAddon):
    settings_model = ToastNotifySettings
  
    async def get_default_settings(self):
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_TOASTNOTIFY_SETTINGS)