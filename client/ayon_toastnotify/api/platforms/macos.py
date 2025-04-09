import os
import subprocess
from typing import Dict, Any, Optional, List

from .base import ToastNotifyPlatformBase
from ..logger import log

class ToastNotifyMacOSPlatform(ToastNotifyPlatformBase):
    """macOS-specific implementation using osascript."""
    
    def show_notification(
        self, 
        title: str, 
        message: str, 
        icon: Optional[str] = None,
        timeout: int = 5,  # Not used in macOS
        actions: List[Dict[str, Any]] = None  # Not supported in basic macOS notifications
    ) -> bool:
        """Show a macOS notification using osascript."""
        try:
            # Escape single quotes in title and message
            title = title.replace("'", "'\\''")
            message = message.replace("'", "'\\''")
            
            # Construct the AppleScript
            script = f'''
            display notification "{message}" with title "{title}"
            '''
            
            # Add subtitle if provided in actions
            if actions and len(actions) > 0:
                for action in actions:
                    if action.get("text"):
                        subtitle = action["text"].replace("'", "'\\''")
                        script = f'''
                        display notification "{message}" with title "{title}" subtitle "{subtitle}"
                        '''
                        break
            
            # Run the osascript command
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                log.error(f"Failed to show notification: {result.stderr}")
                return False
                
            return True
            
        except Exception as e:
            log.error(f"Error showing macOS notification: {e}")
            return False