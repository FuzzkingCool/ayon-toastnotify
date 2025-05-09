# -*- coding: utf-8 -*-
"""Settings for ayon-toastnotify addon."""
from pydantic import Field
from ayon_server.settings import BaseSettingsModel, SettingsField


__version__ = "0.1.5"


class ToastNotifySettings(BaseSettingsModel):
    """Toast notification settings."""
    enabled: bool = SettingsField(True, title="Enabled")
    
    use_fixed_port: bool = SettingsField(
        False, 
        title="Use Fixed Port",
        description="If enabled, use the specified port instead of a random port"
    )
    
    http_port: int = SettingsField(
        5127, 
        title="ToastNotify Port",
        description="Port used for ToastNotify service when fixed port is enabled"
    )
    
    app_id = Field(
        "ToastNotifyApp",
        title="App ID",
        description="Unique identifier for the ToastNotify application"
    )

    notification_timeout: int = Field(
        5,
        title="Notification Timeout", 
        description="Default timeout in seconds for notifications"
    )
    
    windows_powershell_path: str = Field(
        "powershell.exe",
        title="PowerShell Path",
        description="Path to PowerShell executable (Windows only)"
    )

    

# Default settings
DEFAULT_TOASTNOTIFY_SETTINGS = {
    "use_fixed_port": False,
    "http_port": 5127,
    "enabled": True,
    "app_id": "AYON.ToastNotify",
    "notification_timeout": 5,
    "windows_powershell_path": "powershell.exe"

}
