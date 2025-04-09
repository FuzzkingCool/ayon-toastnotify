import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

from ..logger import log

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
        actions: List[Dict[str, str]] = None
    ) -> bool:
        """
        Show a toast notification.
        
        Args:
            title: The notification title
            message: The notification message
            icon: Path to an icon file or None for default
            timeout: Timeout in seconds
            actions: List of action buttons to show (platform dependent)
            
        Returns:
            bool: True if notification was shown successfully
        """
        raise NotImplementedError("Subclasses must implement show_notification")
    
    def show_fallback_notification(self, title: str, message: str) -> bool:
        """Show a fallback notification using a simple dialog."""
        try:
            # Try using QT if available
            from qtpy import QtWidgets
            app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
            msgbox = QtWidgets.QMessageBox()
            msgbox.setWindowTitle(title)
            msgbox.setText(message)
            msgbox.setIcon(QtWidgets.QMessageBox.Information)
            
            # Use a timer to auto-close the dialog after 5 seconds
            timer = QtWidgets.QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(msgbox.close)
            timer.start(5000)  # 5 seconds
            
            # Show non-blocking message box
            msgbox.show()
            return True
        except Exception as e:
            self.log.error(f"Failed to show fallback notification: {e}")
            return False

