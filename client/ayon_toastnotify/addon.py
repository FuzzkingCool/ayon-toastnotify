import os
import platform
from pathlib import Path

from ayon_core.addon import AYONAddon, ITrayService

from .version import __version__
from .api.notification_manager import NotificationManager
from .logger import log
from .install_burnttoast import install_burnt_toast, warmup_powershell_session
from .install_alerter import install_alerter
from . import AYON_TOASTNOTIFY_ROOT

class ToastNotifyAddon(AYONAddon, ITrayService):
    """
    Ayon Toast Notify Addon
    """
    # Define the addon name and version
    name = "toastnotify"
    label = "ToastNotify"
    version = __version__

    # Class variable to store platform handler for reuse across notifications
    _platform_handler = None

    def initialize(self, settings):
        """Initialize the addon"""
        # Store settings for later use by tray_init and tray_start
        self.settings = settings.get("toastnotify", {})

        # Explicitly set use_fixed_port if missing
        if "use_fixed_port" not in self.settings:
            self.settings["use_fixed_port"] = False

        log.info(f"ToastNotify addon initialized with settings: {self.settings}")

        # DEBUG ( For Development )
        os.environ["AYON_TOASTNOTIFY_DEBUG"] = "1"

        # Clear any existing AYON_TOASTNOTIFY_PORT env var during init
        if "AYON_TOASTNOTIFY_PORT" in os.environ:
            log.debug(f"Removing stale AYON_TOASTNOTIFY_PORT={os.environ.pop('AYON_TOASTNOTIFY_PORT')}")

    def tray_init(self):
        """
        Initialize the toast notification service.
        This is called when the tray app initializes.
        """
        log.info("ToastNotify tray service initializing...")

        # Initialize platform handler once if on Windows
        if platform.system() == "Windows":
            log.info("Initializing Windows toast notification dependencies")

            # For easier debugging
            if "vendor" in os.listdir(AYON_TOASTNOTIFY_ROOT):
                log.debug(f"Vendor directory contents: {os.listdir(Path(AYON_TOASTNOTIFY_ROOT) / 'vendor')}")
            else:
                log.error(f"Vendor directory not found in {AYON_TOASTNOTIFY_ROOT}")

            # Use synchronous installation to ensure BurntToast is ready
            install_success = install_burnt_toast(self.settings, async_install=False)
            if install_success:
                # Warm up PowerShell session to improve first notification performance
                warmup_powershell_session(self.settings)

                # Initialize platform handler once and store for reuse
                log.info("Creating shared Windows platform handler instance")
                from .api.platforms import get_platform_handler
                handler_class = get_platform_handler()
                ToastNotifyAddon._platform_handler = handler_class(self.settings)

                # Register the AppID for the platform handler
                ToastNotifyAddon._platform_handler._ensure_app_id(self.settings["app_id"])

                log.info("Windows platform handler initialized and stored for reuse")
            else:
                log.warning("Failed to install BurntToast. Windows notifications may not work.")

        # Initialize alerter for macOS
        elif platform.system() == "Darwin":
            log.info("Initializing macOS toast notification dependencies")

            # Get the setting for alerts
            alerter_warnings = self.settings.get("alerter_installation_warnings_on_each_launch", False)

            # Install alerter - use async if warnings are disabled to avoid blocking UI
            # Pass the settings to make sure we have the warnings config available
            alerter_path = install_alerter(self.settings, async_install=not alerter_warnings)

            if alerter_path:
                log.info(f"Successfully installed alerter at {alerter_path}")
            else:
                # If we couldn't install alerter and warnings are disabled, just log it and continue
                if not alerter_warnings:
                    log.warning("Failed to install alerter. Will fall back to standard macOS notifications.")
                else:
                    log.warning("Failed to install alerter. macOS notifications may not work.")

        # Get the port and set it in environment before creating NotificationManager
        from .api.notification_manager import get_toast_notify_port

        # Force clear the environment variable before getting a port
        if "AYON_TOASTNOTIFY_PORT" in os.environ:
            log.debug(f"Clearing existing AYON_TOASTNOTIFY_PORT={os.environ.get('AYON_TOASTNOTIFY_PORT')}")
        os.environ.pop("AYON_TOASTNOTIFY_PORT", None)

        port = get_toast_notify_port(self.settings)
        log.debug(f"Port selected for notification service: {port}")

        # Create the notification manager with the port we already determined and the shared platform handler
        self.settings = {**self.settings, "_port": port}  # Add the port to settings

        # Pass the shared platform handler to the notification manager
        self.notification_manager = NotificationManager(self.settings, platform_handler=ToastNotifyAddon._platform_handler)
        log.info("ToastNotify tray service initialized")

    def tray_start(self):
        """
        Start the notification service.
        This is called when the tray app is ready to start services.
        """
        log.info("Starting ToastNotify service...")
        # Start the service here instead of in initialize()
        try:

            self.notification_manager.start()

            # Verify the server actually started
            import time
            time.sleep(0.5)  # Give it a moment to start

            # Test if server is responsive
            from .api.client import ToastNotifyClient
            client = ToastNotifyClient(port=self.settings.get("_port"))
            if client.check_service_health():
                log.info("Toast notification service started successfully and is responding")
            else:
                log.warning("Toast notification service started but is not responding to health checks")
        except Exception as e:
            log.error(f"Failed to start notification service: {e}")
            # Add detailed traceback for debugging
            import traceback
            log.debug(traceback.format_exc())

    def tray_exit(self):
        """
        Clean up when the tray app exits.
        """
        log.info("Shutting down ToastNotify service...")
        try:
            # First stop the notification manager and wait for thread cleanup
            if hasattr(self, 'notification_manager'):
                try:
                    self.notification_manager.stop()
                    log.info("Notification service stopped successfully")
                except Exception as e:
                    log.error(f"Error stopping notification manager: {e}")
                    import traceback
                    log.debug(f"Notification manager stop error details: {traceback.format_exc()}")
                finally:
                    # Ensure notification manager is cleaned up even if stop fails
                    self.notification_manager = None

            # Clean up platform handler if it exists
            if ToastNotifyAddon._platform_handler:
                try:
                    ToastNotifyAddon._platform_handler.cleanup()
                except Exception as e:
                    log.error(f"Error cleaning up platform handler: {e}")
                finally:
                    ToastNotifyAddon._platform_handler = None

            # Clear any environment variables
            if "AYON_TOASTNOTIFY_PORT" in os.environ:
                os.environ.pop("AYON_TOASTNOTIFY_PORT")
            if "AYON_TOASTNOTIFY_DEBUG" in os.environ:
                os.environ.pop("AYON_TOASTNOTIFY_DEBUG")

            # If in debug mode, uninstall BurntToast
            from .install_burnttoast import is_debug_mode, uninstall_burnt_toast
            if is_debug_mode() and platform.system() == "Windows":
                log.info("Debug mode detected - attempting to uninstall BurntToast")
                try:
                    uninstall_burnt_toast()
                except Exception as e:
                    log.error(f"Error uninstalling BurntToast: {e}")

        except Exception as e:
            log.error(f"Error stopping notification service: {e}")
            import traceback
            log.debug(f"Shutdown error details: {traceback.format_exc()}")
        finally:
            # Final cleanup to ensure no references remain
            self.settings = {}

