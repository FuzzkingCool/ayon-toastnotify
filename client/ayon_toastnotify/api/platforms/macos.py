import os
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
import tempfile
import threading
import time

from .base import ToastNotifyPlatformBase
from ..logger import log
from ...install_alerter import install_alerter

class ToastNotifyMacOSPlatform(ToastNotifyPlatformBase):
    """macOS-specific implementation using alerter."""
    
    def __init__(self, alerter_path=None):
        """Initialize macOS platform handler."""
        self.alerter_path = alerter_path
        log.debug(f"Initializing MacOS platform with alerter: {alerter_path}")
        
        # If alerter_path is None or not a string, we'll try to get it when needed
        if not self.alerter_path or not isinstance(self.alerter_path, (str, bytes, os.PathLike)):
            log.debug("Alerter path is not valid, will be obtained when needed")
            self.alerter_path = None
        
    def show_notification(
        self, 
        title: str, 
        message: str, 
        icon: Optional[str] = None,
        timeout: int = 5,
        actions: List[Dict[str, Any]] = None,
        on_action: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> bool:
        """Show a macOS notification using alerter."""
        try:
            # Re-check the path to make sure it's available
            if not self.alerter_path:
                self.alerter_path = install_alerter(None, async_install=False)
                
            if not self.alerter_path:
                log.error("Could not get alerter path, notification failed")
                return False
        
            # Create a temporary file to capture the response
            response_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
            response_path = response_file.name
            response_file.close()
        
            # Get the app bundle path
            app_path = Path(self.alerter_path).parent.parent.parent
        
            # Launch using 'open' command which is more reliable for macOS apps
            cmd = ['open', '-a', str(app_path), '--args']
        
            # Add the notification parameters
            cmd.extend(['-message', message])
        
            if title:
                cmd.extend(['-title', title])
            
            if timeout > 0:
                cmd.extend(['-timeout', str(timeout)])
            
            # Add actions if provided
            if actions and len(actions) > 0:
                action_strs = [a.get('title', 'Action') for a in actions]
                cmd.extend(['-actions', ','.join(action_strs)])
                
            # Add output file for response
            cmd.extend(['-output', response_path])
            
            # Add remove option to prevent notification center buildup
            cmd.extend(['-remove'])
            
            # When executing alerter, add a time delay to ensure it's visible
            # and use a group to manage related notifications
            cmd.extend(['-timeout', '10'])  # Longer timeout
            cmd.extend(['-sound', 'default'])  # Add sound
            cmd.extend(['-group', 'ayon_alerts'])  # Group related notifications
            
            # Add these parameters to make notifications more visible
            cmd.extend(['-sound', 'default'])  # Add sound to draw attention
            cmd.extend(['-ignoreDnD'])  # Ignore Do Not Disturb mode
            
            # The NSUserNotificationAlertStyle is already set to "alert" in the Info.plist
            # which should help make it appear as an alert rather than banner
            
            log.debug(f"Executing alerter command: {cmd}")
        
            # Run the alerter with open command
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
        
            # Check if it started
            try:
                returncode = process.wait(timeout=0.5)
                if returncode != 0:
                    log.error(f"Alerter failed with code {returncode}: {process.stderr.read()}")
                    # Delete response file
                    try:
                        os.unlink(response_path)
                    except:
                        pass
                    return False
            except subprocess.TimeoutExpired:
                # This is good - means it's running
                log.debug("Alerter process running in background")
                
                # Start a thread to wait for the process to complete and process the response
                threading.Thread(
                    target=self._process_alerter_response,
                    args=(response_path, on_action, process),
                    daemon=True
                ).start()
                return True
        
        except Exception as e:
            log.error(f"Error showing macOS notification: {e}")
            return False
        
    def _find_terminal_notifier(self):
        """Find terminal-notifier if installed."""
        paths = [
            "/usr/local/bin/terminal-notifier",
            "/opt/homebrew/bin/terminal-notifier",
        ]
        
        for path in paths:
            if os.path.exists(path):
                return path
        
        # Try to find it in PATH
        try:
            result = subprocess.run(
                ["which", "terminal-notifier"], 
                capture_output=True, 
                text=True, 
                check=False
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
            
        return None

    def _process_alerter_response(self, response_path, on_action, process=None):
        """Process the alerter response from the output file.
        
        Args:
            response_path: Path to the temporary response file
            on_action: Callback function for notification actions
            process: Optional subprocess object for process management
        """
        try:
            # Wait for the file to be written
            max_wait = 60  # 1 minute max
            while max_wait > 0 and not os.path.exists(response_path):
                time.sleep(1)
                max_wait -= 1
                
            if not os.path.exists(response_path):
                log.warning("Timeout waiting for alerter response file")
                return
                
            # Read the response
            with open(response_path, 'r') as f:
                response = f.read().strip()
                
            log.debug(f"Alerter response: {response}")
            
            # Clean up the file
            try:
                os.unlink(response_path)
            except Exception as e:
                log.warning(f"Failed to delete response file: {e}")
                
            # Process the response
            if response == "@CLOSED" or response == "@TIMEOUT":
                # User dismissed or timeout occurred
                pass
            elif response == "@CONTENTCLICKED":
                # Content was clicked, treat as default action
                on_action("default")
            elif response.startswith("@ACTIONCLICKED"):
                # An action button was clicked
                on_action(response)
            else:
                # A specific action was selected
                on_action(response)
                
        except Exception as e:
            log.error(f"Error processing alerter response: {e}")