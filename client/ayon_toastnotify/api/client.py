import os
import platform
import json
import threading
import urllib.request
import urllib.error
import socket
import time
from typing import Dict, Any, Optional, List, Callable

from ..logger import log
from .platforms import get_platform_handler
from ..addon import ToastNotifyAddon

class ToastNotifyClient:
    """
    Client for sending requests to the ToastNotify HTTP API.
    """
    
    def __init__(self, host="localhost", port=5127, timeout=5.0):
        """
        Initialize the ToastNotify client.
        
        Args:
            host (str): The host where the ToastNotify service is running
            port (int): The port the ToastNotify service is listening on
            timeout (float): Request timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self._platform_handler = None
        
    @property
    def platform_handler(self):
        """Lazy load the platform handler when needed"""
        # First try to use the shared handler from the addon
        if ToastNotifyAddon._platform_handler is not None:
            return ToastNotifyAddon._platform_handler
            
        # Fall back to creating a new one only if necessary
        if self._platform_handler is None:
            try:
                handler_class = get_platform_handler()
                self._platform_handler = handler_class({})
            except Exception as e:
                log.error(f"Failed to initialize fallback platform handler: {e}")
        return self._platform_handler
        
    def send_notification(
        self,
        title: str,
        message: str,
        icon: Optional[str] = None,
        timeout: int = 5,
        actions: List[Dict[str, Any]] = None,
        platform_options: Dict[str, Dict[str, Any]] = None,
        on_action: Optional[Callable[[str], None]] = None  # New parameter for button clicks
    ) -> bool:
        """
        Send a notification request to the ToastNotify service.
        
        Args:
            title (str): Notification title
            message (str): Notification message
            icon (str, optional): Path to an icon file
            timeout (int): Notification timeout in seconds
            actions (list): List of action buttons to display
            platform_options (dict): Platform-specific options dictionary
            on_action (Callable, optional): Function to call when a button is clicked, receives action ID
            
        Returns:
            bool: True if notification was sent successfully
        """
        # First try the HTTP service
        if self._try_http_notification(title, message, icon, timeout, actions, platform_options, on_action):
            return True
 
        if self.platform_handler:
            try:
                system = platform.system().lower()
                specific_options = {}
                
                # Extract platform-specific options if available
                if platform_options and system in platform_options:
                    specific_options = platform_options[system]
                    
                return self.platform_handler.show_notification(
                    title=title,
                    message=message,
                    icon=icon,
                    timeout=timeout,
                    actions=actions or [],
                    on_action=on_action,  # Pass the on_action parameter
                    **specific_options
                )
            except Exception as e:
                log.error(f"Error in fallback notification: {e}")
                
        return False
    
    def _try_http_notification(
        self,
        title: str,
        message: str,
        icon: Optional[str] = None,
        timeout: int = 5,
        actions: List[Dict[str, Any]] = None,
        platform_options: Dict[str, Dict[str, Any]] = None,
        on_action: Optional[Callable[[str], None]] = None  # Add this parameter
    ) -> bool:
        """Try to send notification via HTTP service."""
        try:
            # IMPORTANT: If we have on_action callback but using HTTP, we need to
            # fall back to direct platform handler since HTTP doesn't support callbacks
            if on_action and actions:
                return False  # Skip HTTP for notifications with callbacks
            
            # Prepare request data
            data = {
                "title": title,
                "message": message,
                "timeout": timeout,
                "actions": actions or []
            }
            
            if icon:
                data["icon"] = icon
                
            if platform_options:
                data["platform_options"] = platform_options
                
            # Convert data to JSON
            json_data = json.dumps(data).encode('utf-8')
            
            # Create request
            url = f"http://{self.host}:{self.port}/notify"
            headers = {"Content-Type": "application/json"}
            req = urllib.request.Request(
                url=url,
                data=json_data,
                headers=headers,
                method="POST"
            )
            
            # Send request with retry for connection errors
            max_retries = 1  # Reduced retries to make fallback quicker
            retry_count = 0
            
            while retry_count <= max_retries:
                try:
                    with urllib.request.urlopen(req, timeout=self.timeout) as response:
                        if response.status == 200:
                            response_data = json.loads(response.read().decode('utf-8'))
                            return response_data.get("status") == "success"
                        return False
                except (urllib.error.URLError, socket.timeout) as e:
                    retry_count += 1
                    if retry_count > max_retries:
                        log.warning(f"HTTP notification service unavailable: {e}")
                        return False
                    log.warning(f"Failed to connect, retry {retry_count}/{max_retries}")
                    time.sleep(0.5)  # Short delay before retry
                
        except Exception as e:
            log.error(f"Error in HTTP notification: {e}")
            return False
            
    def check_service_health(self) -> bool:
        """
        Check if the ToastNotify service is running.
        
        Returns:
            bool: True if service is running and healthy
        """
        try:
            # Create request
            url = f"http://{self.host}:{self.port}/health"
            req = urllib.request.Request(url=url, method="GET")
            
            # Send request
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    response_data = json.loads(response.read().decode('utf-8'))
                    return response_data.get("status") == "ok"
                return False
                
        except urllib.error.URLError:
            # Service is not running
            return False
        except Exception as e:
            log.error(f"Unexpected error checking service health: {e}")
            return False


# Optimize the send_notification function

def _send_async(client, title, message, icon, timeout, actions, platform_options, callback, on_action):
    """Run notification in a separate thread to avoid blocking."""
    try:
        result = client.send_notification(
            title=title,
            message=message,
            icon=icon,
            timeout=timeout,
            actions=actions,
            platform_options=platform_options,   
            on_action=on_action
        )
        if callback:
            callback(result)
    except Exception as e:
        log.error(f"Error in async notification: {e}")
        if callback:
            callback(False)

def send_notification(
    title: str,
    message: str,
    icon: Optional[str] = None,
    timeout: int = 5,
    actions: List[Dict[str, Any]] = None,
    platform_options: Dict[str, Dict[str, Any]] = None,
    host: str = "localhost",
    port: int = None,
    async_send: bool = True,
    callback: Optional[Callable[[bool], None]] = None,
    on_action: Optional[Callable[[str], None]] = None,
    **additional_params  # Accept arbitrary kwargs
) -> bool:
    """
    Send a notification using the ToastNotify service.
    
    Args:
        title: Notification title
        message: Notification message
        icon: Path to an icon file (optional)
        timeout: Notification timeout in seconds
        actions: List of action buttons [{"id": "action1", "text": "Click Me"}]
        platform_options: Platform-specific options dictionary
        host: Notification service host
        port: Notification service port (uses AYON_TOASTNOTIFY_PORT env var if not specified)
        async_send: If True, runs notification in background thread
        callback: Function to call with result when notification completes
        on_action: Function to call when a button is clicked, receives action ID
        **additional_params: Additional parameters passed to the platform handler
        
    Returns:
        bool: True if notification was dispatched successfully
    """
    # Process additional parameters by adding them to platform_options
    system = platform.system().lower()
    platform_options = platform_options or {}
    
    # Make sure there's an entry for the current platform
    if system not in platform_options:
        platform_options[system] = {}
        
    # Add any additional parameters to the platform options
    for key, value in additional_params.items():
        platform_options[system][key] = value

    if port is None:
        try:
            env_port = os.environ.get("AYON_TOASTNOTIFY_PORT")
            if env_port:
                port = int(env_port)
                log.debug(f"Using port {port} from AYON_TOASTNOTIFY_PORT environment variable")
            else:
                # Generate a temporary random port as last resort
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind(('', 0))
                port = s.getsockname()[1]
                s.close()
                log.warning(f"No port found in environment, using temporary random port: {port}")
        except Exception as e:
            # Only as absolute last resort
            import random
            port = random.randint(10000, 65000)
            log.error(f"Error determining port: {e}, using random fallback: {port}")
    
    client = ToastNotifyClient(host=host, port=port)
    
    if async_send:
        thread = threading.Thread(
            target=_send_async,
            args=(client, title, message, icon, timeout, actions, platform_options, callback, on_action)
        )
        thread.daemon = True
        thread.start()
        return True
    else:
        return client.send_notification(
            title=title,
            message=message,
            icon=icon,
            timeout=timeout,
            actions=actions,
            platform_options=platform_options,
            on_action=on_action
        )

def send_progress_notification(
    title: str,
    message: str,
    progress_value: float,
    progress_status: str = "Processing...",
    icon: Optional[str] = None,
    unique_identifier: Optional[str] = None,
    suppress_popup: bool = False,
    sound: Optional[str] = None,
    host: str = "localhost",
    port: int = None,
    async_send: bool = True,  # Default to async for better UI responsiveness
    **additional_params
) -> bool:
    """
    Send a notification with a progress bar.
    
    Args:
        title: Notification title
        message: Notification message
        progress_value: Progress value between 0.0 and 1.0 (0-100%)
        progress_status: Text to display next to the progress bar
        icon: Path to an icon file (optional)
        unique_identifier: Unique identifier for updating the same notification
        suppress_popup: If True, updates silently without showing a new popup
        sound: Sound to play (e.g., "Default", "IM", "Mail", "Reminder", "SMS", "Alarm")
        host: Notification service host
        port: Notification service port (uses AYON_TOASTNOTIFY_PORT env var if not specified)
        async_send: If True, runs PowerShell command in background thread
        **additional_params: Additional platform-specific parameters
        
    Returns:
        bool: True if notification was sent successfully
    """
    # Get port from environment if not specified
    if port is None:
        try:
            env_port = os.environ.get("AYON_TOASTNOTIFY_PORT")
            if env_port:
                port = int(env_port)
            else:
                # Generate a temporary random port as last resort
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind(('', 0))
                port = s.getsockname()[1]
                s.close()
        except Exception:
            # Only as absolute last resort
            import random
            port = random.randint(10000, 65000)
    
    # We can't use the HTTP service for progress bars, so use direct access to platform handler
    client = ToastNotifyClient(host=host, port=port)
    
    # Get direct access to platform handler
    platform_handler = client.platform_handler
    
    if not platform_handler:
        return False
        
    # Check if the platform handler supports progress bars
    if not hasattr(platform_handler, 'show_progress_notification'):
        log.error("Progress notifications are not supported on this platform")
        return False
        
    # Pass all parameters to the platform handler
    return platform_handler.show_progress_notification(
        title=title,
        message=message,
        progress_value=progress_value,
        progress_status=progress_status,
        icon=icon,
        unique_identifier=unique_identifier,
        suppress_popup=suppress_popup,
        sound=sound,
        async_send=async_send,  # Pass the async_send parameter
        **additional_params
    )

