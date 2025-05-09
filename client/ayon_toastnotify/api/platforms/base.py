import os
import subprocess
import platform
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

from ...logger import log

class ToastNotifyPlatformBase:
    """
    Base class for platform-specific implementations of ToastNotify.
    """
    def __init__(self, settings):
        self.log = log
        self.settings = settings
        
    def show_notification(
        self, 
        title: str, 
        message: str, 
        icon: Optional[str] = None,
        timeout: int = 5,
        actions: List[Dict[str, str]] = None,
        on_action: Optional[Callable[[str], None]] = None,  # Add this parameter
        **kwargs  # Add this to accept additional parameters
    ) -> bool:
        """
        Show a toast notification.
        
        Args:
            title: The notification title
            message: The notification message
            icon: Path to an icon file or None for default
            timeout: Timeout in seconds
            actions: List of action buttons to show (platform dependent)
            on_action: Callback function when buttons are clicked
            **kwargs: Additional platform-specific parameters
            
        Returns:
            bool: True if notification was shown successfully
        """
        raise NotImplementedError("Subclasses must implement show_notification")
    
    def show_fallback_notification(self, title: str, message: str) -> bool:
        """Show a fallback notification using a simple dialog or console output."""
        try:
            # Try using console output first as it's safest
            print(f"\n[NOTIFICATION] {title}: {message}\n")
            
            # On macOS, also try using the native 'osascript' command which is thread-safe
            if platform.system() == "Darwin":
                try:
                    # Escape quotes in the message and title
                    safe_title = title.replace('"', '\\"')
                    safe_message = message.replace('"', '\\"')
                    
                    # Use osascript to show a notification
                    subprocess.run([
                        "osascript", 
                        "-e", 
                        f'display notification "{safe_message}" with title "{safe_title}"'
                    ], check=False)
                    return True
                except Exception as e:
                    log.error(f"Failed to show osascript notification: {e}")
            
            # Only try GUI approach if we're on the main thread
            # This avoids the threading crash
            import threading
            if threading.current_thread() is threading.main_thread():
                try:
                    # Try using QT if available and on main thread
                    from qtpy import QtWidgets, QtCore
                    
                    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
                    msgbox = QtWidgets.QMessageBox()
                    msgbox.setWindowTitle(title)
                    msgbox.setText(message)
                    msgbox.setIcon(QtWidgets.QMessageBox.Information)
                    
                    # Use a timer to auto-close the dialog after 5 seconds
                    timer = QtCore.QTimer()
                    timer.setSingleShot(True)
                    timer.timeout.connect(msgbox.close)
                    timer.start(5000)  # 5 seconds
                    
                    # Show non-blocking message box
                    msgbox.show()
                    return True
                except Exception as e:
                    log.error(f"Failed to show QT fallback notification: {e}")
            
            # We showed the console notification at least
            return True
            
        except Exception as e:
            log.error(f"Failed to show any fallback notification: {e}")
            return False

