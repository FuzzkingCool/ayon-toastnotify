import os
import subprocess
from typing import Dict, Any, Optional, List

from .base import ToastNotifyPlatformBase
from ...logger import log

class ToastNotifyLinuxPlatform(ToastNotifyPlatformBase):
    """Linux-specific implementation using notify-send."""
    
    def __init__(self, settings, project_name=None):
        super().__init__(settings)
        # Check if notify-send is available
        self.notify_send_available = self._check_notify_send()
        
    def _check_notify_send(self) -> bool:
        """Check if notify-send is available."""
        try:
            result = subprocess.run(
                ["which", "notify-send"],
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def show_notification(
        self, 
        title: str, 
        message: str, 
        icon: Optional[str] = None,
        timeout: int = 5,
        actions: List[Dict[str, Any]] = None  # Not supported in basic notify-send
    ) -> bool:
        """Show a Linux notification using notify-send."""
        if not self.notify_send_available:
            log.error("notify-send is not available")
            return False
            
        try:
            # Prepare command
            cmd = ["notify-send"]
            
            # Add title
            cmd.append(title)
            
            # Add message
            cmd.append(message)
            
            # Add timeout (in milliseconds)
            cmd.extend(["--expire-time", str(timeout * 1000)])
            
            # Add icon if provided
            if icon and os.path.exists(icon):
                cmd.extend(["--icon", icon])
                
            # Run the notify-send command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                log.error(f"Failed to show notification: {result.stderr}")
                return False
                
            return True
            
        except Exception as e:
            log.error(f"Error showing Linux notification: {e}")
            return False