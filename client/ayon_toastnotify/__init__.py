from pathlib import Path

# Define the root directory of the addon
AYON_TOASTNOTIFY_ROOT = Path(__file__).parent.absolute()

from .version import __version__
from .api.client import send_notification, send_progress_notification, ToastNotifyClient
from .installer import install_burnt_toast
from .addon import ToastNotifyAddon

__all__ = [
    "__version__",
    "ToastNotifyAddon",
    "AYON_TOASTNOTIFY_ROOT",
    "send_notification",
    "send_progress_notification",
    "ToastNotifyClient",
    "install_burnt_toast",
    "AYON_TOASTNOTIFY_ROOT"
]