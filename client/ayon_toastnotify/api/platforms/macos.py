import os
import subprocess
import atexit

from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
import tempfile
import threading
import time
from qtpy import QtCore

from .base import ToastNotifyPlatformBase
from ...logger import log
from ...install_alerter import install_alerter
from ...version import __version__ as addon_version

from ayon_api import get_addon_project_settings

class ToastNotifyMacOSPlatform(ToastNotifyPlatformBase):
    """macOS-specific implementation using alerter."""

    def __init__(self, alerter_path=None, settings=None, project_name=None):
        """Initialize macOS platform handler."""
        self.alerter_path = alerter_path
        log.debug(f"Initializing MacOS platform with alerter: {alerter_path}")

        # Use provided settings as base
        self.settings = settings or {}

        # Prefer constructor argument, then environment
        if not project_name:
            project_name = os.environ.get("AYON_PROJECT_NAME")

        if project_name:
            try:

                self.settings = get_addon_project_settings(
                    "ayon_toastnotify",
                    addon_version,
                    project_name
                )
            except Exception as e:
                log.warning(f"Failed to fetch project settings for {project_name}: {e}")
        else:
            log.warning("No project name provided; skipping remote settings fetch.")

        self.alerter_installation_warnings_on_each_launch = self.settings.get(
            "alerter_installation_warnings_on_each_launch", False
        )
        # Track all background threads and processes for cleanup
        self._active_threads = []
        self._active_processes = []
        self._cleanup_event = threading.Event()
        # Register cleanup with atexit to ensure it runs on interpreter exit
        atexit.register(self.cleanup)

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
        # Add check to detect if notifications are enabled
        # We'll count errors and prompt after repeated failures
        if not hasattr(self, '_notification_failures'):
            self._notification_failures = 0

        try:

            # If warnings are disabled, silently fall back to osascript
            if not self.alerter_installation_warnings_on_each_launch:
                return self._show_osascript_notification(title, message)
            # Re-check the path to make sure it's available
            if not self.alerter_path:
                # If warnings are disabled, use async_install=False but don't wait for result to avoid UI blocking
                self.alerter_path = install_alerter(None, async_install=not self.alerter_installation_warnings_on_each_launch)

            if not self.alerter_path:
                log.error("Could not get alerter path, notification failed")
                self._notification_failures += 1

                # After 3 failures, suggest enabling notifications ONLY if warnings are enabled
                if self._notification_failures >= 3 and self.alerter_installation_warnings_on_each_launch:
                    self._notification_failures = 0

                    # Import inside function to avoid circular imports
                    from ...install_alerter import prompt_notification_settings

                    # Run on main thread since Qt requires it
                    QtCore.QTimer.singleShot(0, prompt_notification_settings)
                    return False



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
            self._active_processes.append(process)

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

                    # Fall back to osascript if alerter fails
                    return self._show_osascript_notification(title, message)
            except subprocess.TimeoutExpired:
                # This is good - means it's running
                log.debug("Alerter process running in background")

                # Start a thread to wait for the process to complete and process the response
                t = threading.Thread(
                    target=self._process_alerter_response,
                    args=(response_path, on_action, process),
                    daemon=True
                )
                self._active_threads.append(t)
                t.start()
                return True

        except Exception as e:
            log.error(f"Error showing macOS notification: {e}")
            self._notification_failures += 1

            # After 3 failures, suggest enabling notifications ONLY if warnings are enabled
            if self._notification_failures >= 3 and self.alerter_installation_warnings_on_each_launch:
                self._notification_failures = 0

                # Import inside function to avoid circular imports
                from ...install_alerter import prompt_notification_settings

                # Run on main thread since Qt requires it - with a slight delay to avoid UI issues
                QtCore.QTimer.singleShot(100, lambda: prompt_notification_settings())
                return False

            # Fall back to osascript in all other cases
            return self._show_osascript_notification(title, message)

    def _show_osascript_notification(self, title, message):
        """Fall back to standard macOS notifications using osascript."""
        try:
            # Escape double quotes in the message and title
            message = message.replace('"', '\\"')
            title = title.replace('"', '\\"')

            # Create the AppleScript command
            script = f'''
            display notification "{message}" with title "{title}"
            '''

            # Run the osascript command
            process = subprocess.Popen(
                ["osascript", "-e", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for it to complete
            returncode = process.wait(timeout=1)
            if returncode != 0:
                log.warning(f"osascript notification failed: {process.stderr.read()}")
                return False

            return True

        except Exception as e:
            log.error(f"Error showing osascript notification: {e}")
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

    def cleanup(self):
        """Clean up all background threads and processes to allow app exit."""
        log.info("ToastNotifyMacOSPlatform cleanup: Stopping all background threads and processes.")
        self._cleanup_event.set()
        # Terminate all active processes
        for proc in self._active_processes:
            try:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except Exception:
                        proc.kill()
            except Exception as e:
                log.warning(f"Failed to terminate process: {e}")
        self._active_processes.clear()
        # Join all active threads
        for t in self._active_threads:
            try:
                if t.is_alive():
                    t.join(timeout=2)
            except Exception as e:
                log.warning(f"Failed to join thread: {e}")
        self._active_threads.clear()
        log.info("ToastNotifyMacOSPlatform cleanup complete.")
        import platform
        import os
        if platform.system() == "Darwin":
            log.info("Forcing process exit on macOS to ensure no lingering process.")
            os._exit(0)

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
                if self._cleanup_event.is_set():
                    return
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
                if on_action:
                    on_action("default")
            elif response.startswith("@ACTIONCLICKED"):
                # An action button was clicked
                if on_action:
                    on_action(response)
            else:
                # A specific action was selected
                if on_action:
                    on_action(response)

        except Exception as e:
            log.error(f"Error processing alerter response: {e}")
