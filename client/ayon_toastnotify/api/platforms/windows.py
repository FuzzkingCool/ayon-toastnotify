import os
from pathlib import Path
import re
import uuid
import subprocess
from typing import Dict, Any, Optional, List, Callable
import zipfile

from .base import ToastNotifyPlatformBase
from ..logger import log

def _create_hidden_startupinfo():
    """Create startupinfo object to hide console window"""
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0  # SW_HIDE
    return startupinfo

class ToastNotifyWindowsPlatform(ToastNotifyPlatformBase):
    """Windows implementation using BurntToast PowerShell module."""
    
    def __init__(self, settings):
        super().__init__(settings)
        self.powershell_path = settings.get("windows_powershell_path", "powershell.exe")
        self.app_id = settings.get("app_id", "AYON.ToastNotify")

        #@TODO: We shouldn't have to do this on every Platform initialization. 
        self.burnt_toast_available = self._check_burnt_toast_available()

        #This probably needs to be done on every launch, but we can optimize it later
        self.powershell_version = self._get_powershell_version()
        self.supports_events = self._check_events_supported()
        log.debug(f"PowerShell version: {self.powershell_version}, Events supported: {self.supports_events}")
        log.info(f"ToastNotifyWindowsPlatform initialized with PowerShell path: {self.powershell_path}")

        #@TODO: We shouldn't have to do this on every Platform initialization. 
        self._ensure_app_id(self.app_id)

        #@TODO: We shouldn't have to do this on every launch or Platform initialization. 
        self.urlprotocol_registered =  self._ensure_silent_protocol_handler(settings.get("port", os.environ.get("AYON_TOASTNOTIFY_PORT", "5127")))
        log.debug(f"URL protocol handler registered: {self.urlprotocol_registered}")

        #Use regular string instead of f-string for command template
        self._ps_command = (
            '$ProgressPreference = "SilentlyContinue"; '
            'if (-not (Get-Module BurntToast)) { Import-Module BurntToast -DisableNameChecking -Force }; '
            'New-BurntToastNotification -Text "{0}", "{1}" {2} -AppId "{3}"'
        )
    
    def _get_powershell_version(self):
        """Get the PowerShell version."""
        try:
            result = subprocess.run(
                [
                    self.powershell_path, 
                    "-NoProfile",
                    "-Command", 
                    "$PSVersionTable.PSVersion.ToString()"
                ],
                capture_output=True,
                text=True,
                check=False,
                startupinfo=_create_hidden_startupinfo()
            )
            
            if result.returncode == 0 and result.stdout:
                return result.stdout.strip()
            return "Unknown"
        except Exception as e:
            log.error(f"Error getting PowerShell version: {e}")
            return "Unknown"

    def _check_events_supported(self):
        """Check if PowerShell version supports toast events."""
        try:
            if self.powershell_version == "Unknown":
                return False
            
            # Parse the version string
            match = re.match(r"(\d+)\.(\d+)\.(\d+)", self.powershell_version)
            if match:
                major, minor, build = map(int, match.groups())
                # PowerShell 7.1.0 or higher supports events
                return (major > 7) or (major == 7 and minor >= 1)
            return False
        except Exception:
            return False
    
    def _check_burnt_toast_available(self) -> bool:
        """Check if BurntToast module is available."""
        try:
            # More thorough check with better error handling
            ps_script = """
            $ProgressPreference = "SilentlyContinue"
            try {
                # Check for module by path first (for bundled version)
                $userModules = Join-Path -Path ([Environment]::GetFolderPath('MyDocuments')) -ChildPath "WindowsPowerShell\\Modules\\BurntToast"
                $systemModules = "$env:ProgramFiles\\WindowsPowerShell\\Modules\\BurntToast"
                
                if ((Test-Path $userModules) -or (Test-Path $systemModules)) {
                    # Import to verify it loads properly
                    Import-Module BurntToast -DisableNameChecking -Force
                    
                    # Try a basic function to confirm it's working
                    $null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
                    Write-Output "BurntToast module is available and working"
                    exit 0
                }
                
                # Try standard module check as fallback
                if (Get-Module -ListAvailable BurntToast) {
                    Write-Output "BurntToast module is available"
                    exit 0
                }
                
                Write-Output "BurntToast module is NOT available"
                exit 1
            } catch {
                Write-Output "Error checking BurntToast: $_"
                exit 1
            }
            """
            
            result = subprocess.run(
                [self.powershell_path, "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                check=False,
                startupinfo=_create_hidden_startupinfo()
            )
            
            if "is available" in result.stdout and result.returncode == 0:
                log.info("BurntToast module is available")
                return True
            else:
                log.warning(f"BurntToast module check failed: {result.stdout}")
                return False
                    
        except Exception as e:
            log.error(f"Error checking for BurntToast: {e}")
            return False
    
    def _ensure_app_id(self, app_id):
        """Ensure the specified app ID is registered for BurntToast."""
        try:
            # Register the AppId manually with more reliable approach
            ps_cmd = f"""
            $ProgressPreference = "SilentlyContinue"
            
            try {{
                # Load BurntToast module
                Import-Module BurntToast -DisableNameChecking -Force
                
                # Directly create registry key for AppId (more reliable than New-BTAppId)
                $path = "HKCU:\\SOFTWARE\\Classes\\AppUserModelId\\{app_id}"
                
                if (-not (Test-Path $path)) {{
                    New-Item -Path $path -Force | Out-Null
                    New-ItemProperty -Path $path -Name "DisplayName" -Value "AYON ToastNotify" -PropertyType String -Force | Out-Null
                    Write-Output "AppID registration successful (direct registry)"
                }} else {{
                    Write-Output "AppID already registered"
                }}
                
                # Verify registration
                if (Test-Path $path) {{
                    # Registration succeeded, use this app ID
                    Write-Output "Using app ID: {app_id}"
                }} else {{
                    # Registration failed, fall back to built-in
                    Write-Output "Using Windows built-in app ID"
                }}
            }} catch {{
                Write-Output "Registration error: $_"
                Write-Output "Using Windows built-in app ID"
            }}
            """
            
            result = subprocess.run(
                [self.powershell_path, "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                check=False,
                startupinfo=_create_hidden_startupinfo()
            )
            
            log.debug(f"AppID setup result: {result.stdout.strip()}")
            
            # Use the specific app ID only if registration was successful
            if "Using app ID:" in result.stdout and app_id in result.stdout:
                self.app_id = app_id
                return True
            else:
                # Fall back to Windows built-in app ID
                self.app_id = "Windows.SystemToast.Winstore.App"
                return False
                
        except Exception as e:
            log.error(f"Error setting up AppID: {e}")
            self.app_id = "Windows.SystemToast.Winstore.App"  # Fallback
            return False
    
    def _ensure_silent_protocol_handler(self, port):
        """Register a custom protocol handler that silently forwards to our HTTP service."""
        try:
            # Create a dedicated script with better HTTP handling
            script_dir = os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "AYON")
            script_file = os.path.join(script_dir, "ToastHandler.ps1")
            
            # Create directory if it doesn't exist
            os.makedirs(script_dir, exist_ok=True)
            
            # Create a simpler, more direct script that properly handles the protocol
            script_content = f'''
# Toast Handler Script
param($Url)

# Create log directory if it doesn't exist
$logDir = "$env:TEMP\\AYON_Logs"
if (-not (Test-Path $logDir)) {{
    New-Item -Path $logDir -ItemType Directory -Force | Out-Null
}}
$logFile = "$logDir\\toast_handler.log"

function Log-Message($message) {{
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $message" | Out-File -Append -FilePath $logFile
}}

Log-Message "Handler started with URL: $Url"

try {{
    # Extract IDs from URL - using more lenient pattern
    if ($Url -match "ayontoast://([^/]+)/([^/]+)") {{
        $notificationId = $matches[1]
        $actionId = $matches[2]
        
        $httpUrl = "http://localhost:{port}/action/$notificationId/$actionId"
        Log-Message "Sending request to: $httpUrl"
        
        # METHOD 1: Using Invoke-RestMethod which is most reliable
        try {{
            Log-Message "Trying Invoke-RestMethod..."
            Invoke-RestMethod -Uri $httpUrl -Method Get -TimeoutSec 5 -UseBasicParsing
            Log-Message "Invoke-RestMethod SUCCESS"
            exit 0
        }} catch {{
            Log-Message "Invoke-RestMethod failed: $_"
            
            # METHOD 2: Using WebClient as fallback
            try {{
                Log-Message "Trying WebClient..."
                $webClient = New-Object System.Net.WebClient
                $result = $webClient.DownloadString($httpUrl)
                Log-Message "WebClient SUCCESS: $result"
                exit 0
            }} catch {{
                Log-Message "WebClient failed: $_"
                
                # METHOD 3: Using curl as final fallback
                try {{
                    Log-Message "Trying curl..."
                    & curl -s -f "$httpUrl"
                    Log-Message "curl SUCCESS"
                    exit 0
                }} catch {{
                    Log-Message "All methods failed. Giving up."
                    exit 1
                }}
            }}
        }}
    }} else {{
        Log-Message "URL doesn't match expected pattern: $Url"
        exit 1
    }}
}} catch {{
    Log-Message "Unhandled exception: $_"
    exit 1
}}
'''
            
            # Write the script file
            with open(script_file, "w") as f:
                f.write(script_content)
            
            log.debug(f"Created protocol handler script at: {script_file}")
            
            # Create secure registry entry with properly escaped paths
            ps_path = script_file.replace("\\", "\\\\")
            
            # Use Start-Process technique that definitely won't show a window
            ps_command = f'''powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -NoProfile -File "{ps_path}" "%1"'''
            
            # Create registry entries
            ps_script = f'''
            # Set error action to stop so errors are caught
            $ErrorActionPreference = "Stop"
            
            try {{
                $protocolName = "ayontoast"
                $regPath = "HKCU:\\SOFTWARE\\Classes\\$protocolName"
                
                # Create main protocol key
                if (-not (Test-Path $regPath)) {{
                    New-Item -Path $regPath -Force | Out-Null
                }}
                
                # Set protocol properties
                Set-ItemProperty -Path $regPath -Name "(Default)" -Value "AYON Toast Protocol" -Type String -Force
                Set-ItemProperty -Path $regPath -Name "URL Protocol" -Value "" -Type String -Force
                
                # Create command key path
                $cmdPath = "$regPath\\shell\\open\\command"
                if (-not (Test-Path "$regPath\\shell")) {{
                    New-Item -Path "$regPath\\shell" -Force | Out-Null
                }}
                if (-not (Test-Path "$regPath\\shell\\open")) {{
                    New-Item -Path "$regPath\\shell\\open" -Force | Out-Null
                }}
                if (-not (Test-Path $cmdPath)) {{
                    New-Item -Path $cmdPath -Force | Out-Null
                }}
                
                # Set command value - using the escaped path
                $command = '{ps_command}'
                Set-ItemProperty -Path $cmdPath -Name "(Default)" -Value $command -Type String -Force
                
                # Verify registration
                $registeredCmd = Get-ItemProperty -Path $cmdPath -Name "(Default)" -ErrorAction SilentlyContinue
                if ($registeredCmd -and $registeredCmd.'(default)' -eq $command) {{
                    Write-Output "Protocol handler registered successfully"
                }} else {{
                    Write-Output "Protocol registration verification failed"
                    exit 1
                }}
            }} catch {{
                Write-Output "Error registering protocol handler: $_"
                exit 1
            }}
            '''
            
            # Execute the registration script
            result = subprocess.run(
                [self.powershell_path, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                check=False,
                startupinfo=_create_hidden_startupinfo()
            )
            
            if "Protocol handler registered successfully" not in result.stdout:
                log.error(f"Failed to register protocol handler: {result.stderr or result.stdout}")
                return False
                
            log.info("Protocol handler registered successfully")
            
            # Create a test file to verify we can write to the directory
            try:
                test_file = os.path.join(script_dir, "test_write.txt")
                with open(test_file, "w") as f:
                    f.write("Test file to verify write permissions")
                log.debug(f"Test file created successfully at {test_file}")
                os.remove(test_file)
            except Exception as e:
                log.warning(f"Could not write test file to {script_dir}: {e}")
            
            return True
                
        except Exception as e:
            log.error(f"Error registering protocol handler: {e}")
            import traceback
            log.debug(f"Protocol handler error details: {traceback.format_exc()}")
            return False

    def show_notification(
        self, 
        title: str, 
        message: str, 
        icon: Optional[str] = None,
        hero_image: Optional[str] = None,  # Add hero_image parameter
        timeout: int = 5,
        actions: List[Dict[str, Any]] = None,
        on_action: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> bool:
        """Show a Windows toast notification using BurntToast."""
        if not self.burnt_toast_available:
            log.error("BurntToast module is not available. Notification cannot be sent.")
            return False
            
        # If hero_image is provided in kwargs, extract it
        hero_image = kwargs.pop("hero_image", hero_image)
        
        # If actions are provided, use the button-enabled version
        if actions and len(actions) > 0:
            # Use the HTTP-based button implementation
            return self._show_notification_with_buttons(
                title, message, icon, actions, on_action, hero_image=hero_image, timeout=timeout, **kwargs
            )
        else:
            # No buttons, use minimal version
            return self._show_notification_minimal(
                title, message, icon, hero_image=hero_image, actions=actions, on_action=on_action, timeout=timeout, **kwargs
            )

    def _show_notification_minimal(
        self, 
        title: str, 
        message: str, 
        icon: Optional[str] = None,
        hero_image: Optional[str] = None,
        actions: List[Dict[str, Any]] = None,
        on_action: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> bool:
        """Basic notification implementation with support for arbitrary BurntToast parameters."""
        try:
            # Double-check BurntToast is available
            if not self.burnt_toast_available:
                log.error("BurntToast module is not available. Notification cannot be sent.")
                return False
                
            # Get timeout from kwargs ONLY if it wasn't explicitly passed
            timeout = kwargs.get("timeout", 5)

            ## If no timeout is provided, set a default value
            if timeout is None:
                timeout = self.settings.get("notification_timeout", 5)
            
            # Add timeout to kwargs if not already present
            if "timeout" not in kwargs:
                kwargs["timeout"] = timeout
            
            # Escape double quotes in title and message
            title = title.replace('"', '`"')
            message = message.replace('"', '`"')
            
            # Define switch parameters (parameters that don't take values)
            switch_params = ['silent', 'snooze_and_dismiss', 'suppress_popup']
            
            # Prepare parameter parts for PowerShell command
            param_parts = []
            switch_parts = []
            
            # Add basic text parameter
            param_parts.append(f'-Text @("{title}", "{message}")')
            
            # Add AppId
            param_parts.append(f'-AppId "{self.app_id}"')
            
            # Add icon if provided
            if icon and os.path.exists(icon):
                icon_path = icon.replace('\\', '/').replace('"', '`"')
                param_parts.append(f'-AppLogo "{icon_path}"')
                
            # Add hero image if provided
            if hero_image and os.path.exists(hero_image):
                hero_path = hero_image.replace('\\', '/').replace('"', '`"')
                param_parts.append(f'-HeroImage "{hero_path}"')
            
            # Process additional kwargs as BurntToast parameters
            for key, value in kwargs.items():
                # Skip special parameters we handle separately
                if key in ['timeout', 'actions', 'on_action', 'hero_image']:
                    continue
                    
                # Convert snake_case to PascalCase for PowerShell
                ps_key = ''.join(word.capitalize() for word in key.split('_'))
                
                # Handle switch parameters (boolean flags)
                if key.lower() in switch_params:
                    if value:
                        switch_parts.append(f'-{ps_key}')
                    continue
                    
                # Handle other parameter types
                if isinstance(value, bool):
                    if value:
                        param_parts.append(f'-{ps_key} $True')
                    else:
                        param_parts.append(f'-{ps_key} $False')
                elif isinstance(value, (int, float)):
                    param_parts.append(f'-{ps_key} {value}')
                elif isinstance(value, str):
                    value_esc = value.replace('"', '`"')
                    param_parts.append(f'-{ps_key} "{value_esc}"')
                elif value is not None:
                    # Convert everything else to string
                    value_esc = str(value).replace('"', '`"')
                    param_parts.append(f'-{ps_key} "{value_esc}"')
            
            # Combine all parameters
            all_params = ' '.join(param_parts + switch_parts)
            
            # Build the PowerShell command
            ps_script = f"""
            $ErrorActionPreference = "Continue"
            $ProgressPreference = "SilentlyContinue"
            
            try {{ 
                # Guarantee module is loaded
                Import-Module BurntToast -DisableNameChecking -Force
                
                # Create and show notification with direct parameters
                New-BurntToastNotification {all_params}
                
                Write-Host "Notification sent successfully" 
            }} catch {{ 
                Write-Host "ERROR: $_"
                exit 1
            }}
            """
            
            # Run the PowerShell command
            log.debug(f"Running PowerShell command: {ps_script}")
            result = subprocess.run(
                [self.powershell_path, "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                check=False,
                startupinfo=_create_hidden_startupinfo()
            )
            
            if result.returncode != 0:
                log.error(f"Failed to show notification: {result.stderr or result.stdout}")
                return False
                
            log.info(f"Notification result: {result.stdout.strip()}")
            return True
        except Exception as e:
            log.error(f"Error showing Windows notification: {e}")
            return False
 
    def _show_notification_with_buttons(
        self, 
        title: str, 
        message: str, 
        icon: Optional[str] = None,
        actions: List[Dict[str, Any]] = None,
        on_action: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> bool:
        """Show a notification with buttons using our custom protocol handler."""
        try:
            # If no callback needed, use simple version
            if not on_action:
                return self._show_notification_minimal(
                    title, message, icon, actions=actions, **kwargs
                )
            
            # Generate a unique ID for this notification
            notification_id = str(uuid.uuid4())
            
            # Register the callback in our registry
            from ..notification_manager import register_action_callback
            register_action_callback(notification_id, on_action)
            
            # Escape quotes for PowerShell
            title = title.replace('"', '`"')
            message = message.replace('"', '`"')
            
            # Create buttons with CUSTOM PROTOCOL URLs 
            buttons_script = []
            button_vars = []
            
            for idx, action in enumerate(actions):
                action_id = action.get("id", f"action_{idx}")
                button_text = action.get("text", "Button").replace('"', '`"')
                var_name = f"$btn{idx}"
                
                # Use our custom protocol instead of HTTP
                protocol_url = f"ayontoast://{notification_id}/{action_id}"
                
                buttons_script.append(
                    f'{var_name} = New-BTButton -Content "{button_text}" '
                    f'-Arguments "{protocol_url}" -ActivationType Protocol'
                )
                button_vars.append(var_name)
            
            # Add icon if provided
            icon_param = ""
            if icon and os.path.exists(icon):
                icon_path = icon.replace('\\', '/').replace('"', '`"')
                icon_param = f'-AppLogo "{icon_path}"'
                
            # Handle hero image if provided
            hero_param = ""
            if "hero_image" in kwargs and kwargs.get("hero_image") is not None:
                hero_path = kwargs["hero_image"]
                if os.path.exists(hero_path):
                    hero_path = hero_path.replace('\\', '/').replace('"', '`"')
                    hero_param = f'-HeroImage "{hero_path}"'
            
            # Build PowerShell script
            ps_script = (
                "$ErrorActionPreference = \"Continue\"\n"
                "$ProgressPreference = \"SilentlyContinue\"\n"
                "\n"
                "try {\n"
                "    # Import module\n"
                "    Import-Module BurntToast -DisableNameChecking -Force\n"
                "\n"
                "    # Define buttons\n"
                "    " + "\n    ".join(buttons_script) + "\n"
                "\n"
                "    # Create and show notification\n"
                f"    New-BurntToastNotification -Text @(\"{title}\", \"{message}\") {icon_param} {hero_param} -Button @({', '.join(button_vars)}) -AppId \"{self.app_id}\" -UniqueIdentifier \"{notification_id}\"\n"
                "\n"
                "    Write-Output \"Notification with buttons sent successfully\"\n"
                "} catch {\n"
                "    Write-Output \"ERROR: $_\"\n"
                "    exit 1\n"
                "}\n"
            )
            
            # Log a simple message without the full script (avoids Unicode issues)
            log.debug(f"Creating notification with buttons: {title} ({len(actions)} buttons)")
            
            # Run the PowerShell command
            result = subprocess.run(
                [self.powershell_path, "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                check=False,
                startupinfo=_create_hidden_startupinfo()
            )
            
            if result.returncode != 0:
                log.error(f"Failed to show notification: {result.stderr or result.stdout}")
                return False
                
            log.info(f"Notification with buttons result: {result.stdout.strip()}")
            return True
            
        except Exception as e:
            log.error(f"Error showing notification with buttons: {e}")
            return False

    def _ensure_burnttoast_module(self):
        """Ensure BurntToast PowerShell module is available."""
        try:
            # Check if BurntToast is already installed
            check_cmd = [
                self.powershell_path, 
                "-NoProfile", 
                "-Command", 
                "Get-Module -ListAvailable BurntToast"
            ]
            result = subprocess.run(
                check_cmd, 
                capture_output=True, 
                text=True, 
                startupinfo=_create_hidden_startupinfo()
            )
            
            if "BurntToast" in result.stdout:
                log.debug("BurntToast module is already installed.")
                return True
                
            log.info("BurntToast module not found. Installing from bundled zip...")
            
            # Get the path to the bundled zip file
            bundle_dir = Path(__file__).parent.parent.parent / "vendor" / "BurntToast"
            zip_path = bundle_dir / "BurntToast.zip"
            
            if not zip_path.exists():
                log.error(f"BurntToast zip not found at {zip_path}")
                return False
                
            # Extract to PowerShell modules directory
            modules_dir = Path.home() / "Documents" / "WindowsPowerShell" / "Modules" / "BurntToast"
            modules_dir.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(modules_dir)
                
            log.info(f"Successfully extracted BurntToast to {modules_dir}")
            return True
        except Exception as e:
            log.error(f"Failed to install BurntToast module: {e}")
            return False

