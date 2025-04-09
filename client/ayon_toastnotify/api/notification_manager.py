import os
import re
import time
import json
import socket
import threading
import http.server
import socketserver
import platform
import urllib.parse
import subprocess
from typing import Dict, Any, Optional, List, Callable

from .logger import log
from .platforms import get_platform_handler


#Add this to store registered callbacks
_action_callbacks = {}
_action_callback_lock = threading.Lock()

def register_action_callback(notification_id: str, callback: Callable[[str], None]) -> None:
    """Register a callback for a notification ID."""
    with _action_callback_lock:
        _action_callbacks[notification_id] = callback

def handle_action_callback(notification_id: str, action_id: str) -> bool:
    """Handle an action callback for a notification ID."""
    with _action_callback_lock:
        callback = _action_callbacks.get(notification_id)
        if callback:
            try:
                callback(action_id)
                # Remove the callback after it's been called
                _action_callbacks.pop(notification_id, None)
                return True
            except Exception as e:
                log.error(f"Error in action callback: {e}")
    return False

class ToastNotifyHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for toast notifications."""
    
    def log_message(self, format, *args):
        """Override to use our custom logger."""
        log.debug(format % args)

    def do_POST(self):
        """Handle POST requests for notifications."""
        parsed_path = urllib.parse.urlparse(self.path)
        
        if parsed_path.path != "/notify":
            self.send_error(404, "Not Found")
            return
            
        try:
            # Get content length
            content_length = int(self.headers.get('Content-Length', 0))
            
            # Read the request body
            request_body = self.rfile.read(content_length).decode('utf-8')
            
            # Parse JSON
            try:
                notification_data = json.loads(request_body)
            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON")
                return
                
            # Extract notification parameters
            title = notification_data.get("title", "AYON Notification")
            message = notification_data.get("message", "")
            icon = notification_data.get("icon")
            timeout = notification_data.get("timeout", 
                                           self.server.notification_manager.notification_timeout)
            actions = notification_data.get("actions", [])
            platform_options = notification_data.get("platform_options", {})
            
            # Get current platform
            system = platform.system().lower()
            specific_options = {}
            
            # Extract platform-specific options if available
            if system in platform_options:
                specific_options = platform_options[system]
                specific_options.pop("timeout", None)
            
            # Show notification
            result = self.server.notification_manager.show_notification(
                title=title,
                message=message,
                icon=icon,
                timeout=timeout,
                actions=actions,
                callback=None,  # Callbacks aren't supported with REST
                **specific_options
            )
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            response = {"status": "success" if result else "error"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            log.error(f"Error processing notification: {e}")
            self.send_error(500, "Internal Server Error")
            
    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urllib.parse.urlparse(self.path)
        
        # Handle action callbacks
        action_pattern = r'^/action/([^/]+)/([^/]+)$'
        action_match = re.match(action_pattern, parsed_path.path)
        
        if action_match:
            notification_id = action_match.group(1)
            action_id = action_match.group(2)
            
            log.info(f"Button clicked: notification={notification_id}, action={action_id}")
            success = handle_action_callback(notification_id, action_id)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            response = {"status": "success" if success else "error"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return
            
        # Handle health check as before
        if parsed_path.path == "/health":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {"status": "ok", "service": "toastnotify"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_error(404, "Not Found")


class ToastNotifyHTTPServer(socketserver.TCPServer):
    """Custom HTTP server with notification manager reference."""
    allow_reuse_address = True
    
    def __init__(self, server_address, handler_class, notification_manager):
        self.notification_manager = notification_manager
        super().__init__(server_address, handler_class)

class NotificationManager:
    """
    Manages toast notifications across platforms.
    
    Provides an HTTP API for receiving notification requests.
    """
    
    def __init__(self, settings: Dict[str, Any], platform_handler=None):
        """Initialize the notification manager with given settings."""
        self.settings = settings
        # Use pre-determined port if provided, otherwise get a new one
        self.http_port = settings.get("_port") or get_toast_notify_port(settings)
        self.running = False
        self.thread = None
        self.server = None
        self.notification_timeout = settings.get("notification_timeout", 5)
        
        # Set environment variable for other processes to use
        os.environ["AYON_TOASTNOTIFY_PORT"] = str(self.http_port)
        
        # Add debug logging here
        log.info(f"NotificationManager initialized with port: {self.http_port}")
        
        # Use provided platform handler or create a new one if not provided
        self.platform_handler = platform_handler
        
        if self.platform_handler:
            log.info(f"Using provided platform handler: {type(self.platform_handler).__name__}")
        else:
            # Initialize the platform-specific handler
            try:
                platform_handler_class = get_platform_handler()
                self.platform_handler = platform_handler_class(self.settings)
                log.info(f"Initialized new platform handler: {type(self.platform_handler).__name__}")
            except Exception as e:
                log.error(f"Failed to initialize platform handler: {e}")
                self.platform_handler = None
    
    def start(self):
        """Start the notification service."""
        if self.running:
            log.warning("Notification service is already running")
            return
            
        # Since we're now getting the port in __init__, we don't need the port selection logic here
        # Just use self.http_port directly
        log.info(f"Using port {self.http_port} for notification service")
        
        self.running = True
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        log.info(f"Toast notification service started on port {self.http_port}")
        
    def stop(self):
        """Stop the notification service."""
        self.running = False
        
        if self.server:
            try:
                # Create a client connection to break the accept() call
                socket.create_connection(("localhost", self.http_port), timeout=1)
                self.server.shutdown()
                self.server.server_close()
            except Exception as e:
                log.debug(f"Exception during server shutdown: {e}")
                
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
            
        log.info("Toast notification service stopped")
            
    def _run_server(self):
        """Run the HTTP server to handle notification requests."""
        try:
            # Log server startup attempt with port
            log.info(f"Starting HTTP server on localhost:{self.http_port}")
            
            # Import required modules here to avoid potential circular imports
            import http.server
            import socketserver
            import json
            import urllib.parse
            
            # Create server with explicit handler
            self.server = ToastNotifyHTTPServer(
                ("localhost", self.http_port),
                ToastNotifyHandler,
                self
            )
            
            # Log successful server creation
            log.info(f"HTTP server successfully created and listening on port {self.http_port}")
            log.debug("Entering server loop")
            
            # Set a timeout to allow checking the running flag
            self.server.timeout = 1.0
            
            # Main server loop
            while self.running:
                try:
                    self.server.handle_request()
                except Exception as e:
                    log.error(f"Error handling request: {e}")
                    
        except OSError as e:
            # Check for specific error codes
            if hasattr(e, 'errno') and e.errno == 10048:  # Address already in use
                log.error(f"Port {self.http_port} is already in use. Cannot start server.")
            else:
                log.error(f"Failed to start HTTP server: {e}")
            self.running = False
        except Exception as e:
            log.error(f"Unexpected error starting HTTP server: {e}")
            self.running = False
            
    def show_notification(
        self, 
        title: str, 
        message: str, 
        icon: Optional[str] = None,
        timeout: Optional[int] = None,
        actions: List[Dict[str, str]] = None,
        callback: Optional[Callable] = None,
        **platform_specific_options
    ) -> bool:
        """Show a notification using the platform handler."""
        if not self.platform_handler:
            log.error("No platform handler available")
            return False
            
        try:
            return self.platform_handler.show_notification(
                title=title,
                message=message,
                icon=icon,
                timeout=timeout or self.notification_timeout,
                actions=actions or [],
                on_action=callback,
                **platform_specific_options
            )
        except Exception as e:
            log.error(f"Error showing notification: {e}")
            return False
        

# Ensure the port is always set correctly and avoid using a fixed port unless explicitly required
def get_toast_notify_port(settings: Dict[str, Any]) -> int:
    """Get a port for ToastNotify HTTP service and set in environment."""
    # Force clear any existing environment variable
    if "AYON_TOASTNOTIFY_PORT" in os.environ:
        port_value = os.environ.pop("AYON_TOASTNOTIFY_PORT")
        log.debug(f"Cleared existing AYON_TOASTNOTIFY_PORT={port_value}")
    
    # Explicitly check use_fixed_port setting with detailed logging
    use_fixed_port = settings.get("use_fixed_port", False)
    log.debug(f"use_fixed_port setting: {use_fixed_port} (type: {type(use_fixed_port).__name__})")
    
    if use_fixed_port is True:  # Explicit comparison with True
        port = settings.get("http_port", 5127)
        log.info(f"Using fixed port from settings: {port}")
    else:
        # Always get a fresh random port when use_fixed_port is False
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('', 0))
            port = s.getsockname()[1]
            s.close()
            log.info(f"Using random port: {port}")
        except Exception as e:
            # Only as last resort, use random value rather than falling back to 5127
            import random
            port = random.randint(10000, 65000)
            log.warning(f"Socket binding failed: {e}. Using fallback random port: {port}")
    
    # Set the environment variable with the new port
    os.environ["AYON_TOASTNOTIFY_PORT"] = str(port)
    log.debug(f"Set AYON_TOASTNOTIFY_PORT={port} in environment")
    
    return port