import os
import platform
import subprocess
import tempfile
import zipfile
import threading
import time
from pathlib import Path

from . import AYON_TOASTNOTIFY_ROOT
from .logger import log

# Module-level flags to track installation status
_installation_in_progress = False
_installation_completed = False
_installation_result = False
_installation_lock = threading.Lock()

def _create_hidden_startupinfo():
    """Create startupinfo object to hide console window"""
    if platform.system() != "Windows":
        return None
        
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0  # SW_HIDE
    return startupinfo

def _install_from_bundled_zip(powershell_path):
    """Install BurntToast from bundled ZIP file."""
    try:
        log.info("Installing BurntToast from bundled ZIP file")
        
        # Paths
        bundled_zip = AYON_TOASTNOTIFY_ROOT / "vendor" / "BurntToast" / "BurntToast.zip"
        module_path = Path(os.path.expanduser("~")) / "Documents" / "WindowsPowerShell" / "Modules" / "BurntToast"
        
 
        log.debug(f"AYON_TOASTNOTIFY_ROOT: {AYON_TOASTNOTIFY_ROOT}")
        log.debug(f"Target module path: {module_path}")
        
        # Check if ZIP exists
        if not bundled_zip.exists():
            log.error(f"BurntToast.zip not found at {bundled_zip}")
 
            vendor_dir = AYON_TOASTNOTIFY_ROOT / "vendor"
            if vendor_dir.exists():
                log.debug(f"Vendor directory contents: {list(vendor_dir.glob('*'))}")
            else:
                log.error("Vendor directory doesn't exist")
            return False
        
        log.info(f"Found BurntToast.zip at {bundled_zip}")
        log.debug(f"ZIP file size: {bundled_zip.stat().st_size} bytes")
        
        try:
            import shutil
            
            # Create module directory path if needed
            module_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Remove existing module dir if present
            if module_path.exists():
                log.info(f"Removing existing module at {module_path}")
                shutil.rmtree(module_path)
            
            # Create fresh module directory
            module_path.mkdir(parents=True, exist_ok=True)
            
            # Extract with clear debug output
            log.info(f"Extracting ZIP to {module_path}")
            with zipfile.ZipFile(bundled_zip) as zf:
                zf.extractall(module_path)
            
            # Verify extraction worked
            if not any(module_path.glob("*.psd1")):
                log.warning("No .psd1 files found in extracted directory")
                nested_dirs = list(module_path.glob("**/"))
                log.debug(f"Contents after extraction: {nested_dirs}")
                
                # Check for nested dirs and fix if needed
                nested_modules = list(module_path.glob("**/BurntToast.psd1"))
                if nested_modules:
                    log.info(f"Found nested module at {nested_modules[0].parent}")
                    # Move files from nested dir to module root
                    for item in nested_modules[0].parent.glob("*"):
                        target = module_path / item.name
                        if item.is_dir():
                            if target.exists():
                                shutil.rmtree(target)
                            shutil.copytree(item, target)
                        else:
                            shutil.copy2(item, target)
                    log.debug(f"Fixed directory structure: {list(module_path.glob('*.psd1'))}")
            
            # Final verification
            manifest_files = list(module_path.glob("*.psd1"))
            if manifest_files:
                log.info(f"BurntToast module installed successfully: {manifest_files}")
                return True
            else:
                log.error("No .psd1 files found after extracting and fixing structure")
                return False
                
        except Exception as zip_error:
            log.error(f"ZIP extraction error: {zip_error}")
            import traceback
            log.debug(traceback.format_exc())
            return False
            
    except Exception as e:
        log.error(f"Error installing BurntToast from bundled ZIP: {e}")
        import traceback
        log.debug(traceback.format_exc())
        return False

def create_minimal_burnttoast_module():
    """Create a minimal BurntToast module if zip extraction fails."""
    try:
        log.info("Creating minimal BurntToast module as fallback")
        
        # Target directory
        module_path = Path(os.path.expanduser("~")) / "Documents" / "WindowsPowerShell" / "Modules" / "BurntToast"
        module_path.mkdir(parents=True, exist_ok=True)
        
        # Create minimal module files
        manifest_content = """
@{
    ModuleVersion = '0.8.5'
    GUID = '751a2aeb-a68f-422e-a2ea-376bdd81612a'
    Author = 'Josua King'
    CompanyName = 'Domain Group'
    Copyright = '(c) 2015-2021 Josua King. All rights reserved.'
    Description = 'Module for creating and displaying Toast Notifications on Microsoft Windows 10.'
    PowerShellVersion = '5.0'
    FunctionsToExport = @('New-BurntToastNotification', 'New-BTAppId')
    VariablesToExport = '*'
    AliasesToExport = @()
    RootModule = 'BurntToast.psm1'
}
"""
        
        module_content = """
function New-BurntToastNotification {
    [CmdletBinding()]
    param (
        [Parameter(Position = 0)]
        [string[]]$Text,
        
        [Parameter()]
        [string]$AppLogo,
        
        [Parameter()]
        [string]$AppId,
        
        [Parameter()]
        [int]$ExpirationTime = 5
    )
    
    try {
        # Create notification using native Windows API
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
        
        $template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
        $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
        
        $textNodes = $xml.GetElementsByTagName("text")
        $textNodes[0].AppendChild($xml.CreateTextNode($Text[0])) | Out-Null
        
        if ($Text.Length -gt 1) {
            $textNodes[1].AppendChild($xml.CreateTextNode($Text[1])) | Out-Null
        }
        
        if (-not $AppId) {
            $AppId = "Microsoft.Windows.Shell.RunDialog"
        }
        
        $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($AppId)
        $notification = New-Object Windows.UI.Notifications.ToastNotification($xml)
        $notification.ExpirationTime = [DateTimeOffset]::Now.AddSeconds($ExpirationTime)
        $notifier.Show($notification)
        
        Write-Output "Toast notification displayed successfully"
    }
    catch {
        Write-Error "Failed to show notification: $_"
    }
}

function New-BTAppId {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory)]
        [string]$AppId,
        
        [Parameter()]
        [string]$AppDisplayName = "AYON Toast Notify"
    )
    
    try {
        $regPath = "HKCU:\\SOFTWARE\\Classes\\AppUserModelId\\$AppId"
        if (-not (Test-Path $regPath)) {
            New-Item -Path $regPath -Force | Out-Null
            New-ItemProperty -Path $regPath -Name "DisplayName" -Value $AppDisplayName -PropertyType String -Force | Out-Null
            Write-Output "AppId registered: $AppId"
        } else {
            Write-Output "AppId already exists: $AppId"
        }
    }
    catch {
        Write-Error "Failed to register AppId: $_"
    }
}

Export-ModuleMember -Function New-BurntToastNotification, New-BTAppId
"""
        
        # Write the files
        with open(module_path / "BurntToast.psd1", "w") as f:
            f.write(manifest_content.strip())
            
        with open(module_path / "BurntToast.psm1", "w") as f:
            f.write(module_content.strip())
            
        log.info(f"Created minimal BurntToast module at {module_path}")
        return True
        
    except Exception as e:
        log.error(f"Failed to create minimal BurntToast module: {e}")
        return False

def install_burnt_toast(settings, async_install=True):
    """
    Install BurntToast PowerShell module using PowerShell Gallery.
    
    Args:
        settings: Settings dictionary containing configuration options
        async_install: If True, installation runs in a background thread
        
    Returns:
        bool: True if BurntToast is installed or installation started successfully
    """
    global _installation_in_progress, _installation_completed, _installation_result
    
    # Skip if not on Windows
    if platform.system() != "Windows":
        return True
    
    # Check if installation is already in progress or completed
    with _installation_lock:
        if _installation_in_progress:
            log.info("BurntToast installation already in progress")
            return True
        
        if _installation_completed:
            log.info(f"BurntToast installation already completed (success={_installation_result})")
            return _installation_result
    
    # Check if BurntToast is already installed
    powershell_path = settings.get("windows_powershell_path", "powershell.exe")
    
    # Try installing from the bundled zip first (synchronously)
    log.info("Attempting to install BurntToast from bundled zip")
    result = _install_from_bundled_zip(powershell_path)
    
    if result:
        with _installation_lock:
            _installation_completed = True
            _installation_result = True
        log.info("BurntToast installed successfully from bundled zip")
        return True
    
    # If bundled installation failed, try PowerShell Gallery installation
    log.info("Bundled installation failed, trying PowerShell Gallery installation")
    
    # Mark installation as started
    with _installation_lock:
        _installation_in_progress = True
    
    if async_install:
        # Start installation in a background thread
        install_thread = threading.Thread(
            target=_perform_install,
            args=(settings,),
        )
        install_thread.daemon = True
        install_thread.start()
        return True
    else:
        # Run installation synchronously
        return _perform_install(settings)

def _perform_install(settings):
    """Internal function to perform the installation."""
    global _installation_in_progress, _installation_completed, _installation_result
    
    try:
        powershell_path = settings.get("windows_powershell_path", "powershell.exe")
        log.info("Installing BurntToast from PowerShell Gallery")
        
        # Build installation script with more aggressive error handling
        ps_script = """
        # Set error preferences
        $ErrorActionPreference = "Continue"
        $ProgressPreference = "SilentlyContinue"
        
        # Trust the PSGallery
        try {
            Set-PSRepository -Name "PSGallery" -InstallationPolicy Trusted -ErrorAction SilentlyContinue
        } catch {
            Write-Output "Warning: Could not set PSGallery to trusted: $_"
        }
        
        # Force TLS 1.2 for gallery connections
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
        
        try {
            # Check if module is already installed
            if (Get-Module -ListAvailable -Name BurntToast) {
                Write-Output "BurntToast module is already installed"
                exit 0
            }
            
            # Create target directory
            $moduleDir = "$HOME\\Documents\\WindowsPowerShell\\Modules\\BurntToast"
            if (-not (Test-Path $moduleDir)) {
                New-Item -Path $moduleDir -ItemType Directory -Force | Out-Null
                Write-Output "Created directory: $moduleDir"
            }
            
            # Install BurntToast
            Write-Output "Installing BurntToast module..."
            Install-Module -Name BurntToast -Scope CurrentUser -Force -AllowClobber -Verbose
            
            # Verify installation
            if (Get-Module -ListAvailable -Name BurntToast) {
                Write-Output "BurntToast module installed successfully"
                exit 0
            } else {
                Write-Output "BurntToast module installation failed"
                exit 1
            }
        } catch {
            Write-Output "Error installing BurntToast: $_"
            exit 1
        }
        """
        
        # Run the PowerShell script
        log.info("Running BurntToast installation commands")
        result = subprocess.run(
            [powershell_path, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
            check=False,
            startupinfo=_create_hidden_startupinfo()
        )
        
        log.debug(f"PowerShell output: {result.stdout}")
        if result.stderr:
            log.debug(f"PowerShell error: {result.stderr}")
        
        # Check if successful
        success = "module is already installed" in result.stdout or "installed successfully" in result.stdout
        
        if success:
            log.info("BurntToast module installed successfully via PowerShell Gallery")
        else:
            log.error("Failed to install BurntToast module via PowerShell Gallery")
        
        # Mark installation as complete with result
        with _installation_lock:
            _installation_in_progress = False
            _installation_completed = True
            _installation_result = success
            
        return success
            
    except Exception as e:
        log.error(f"Error installing BurntToast: {e}")
        
        # Mark installation as failed
        with _installation_lock:
            _installation_in_progress = False
            _installation_completed = True
            _installation_result = False
        
        return False
    
def warmup_powershell_session(settings):
    """Pre-load PowerShell and BurntToast module once to improve first notification speed."""
    # Skip if not on Windows
    if platform.system() != "Windows":
        return
        
    # Don't warm up if BurntToast isn't available
    if not _installation_completed or not _installation_result:
        return
        
    try:
        log.debug("PowerShell session warm-up initiated")
        powershell_path = settings.get("windows_powershell_path", "powershell.exe")
        
        # Create a script that loads the module and keeps it loaded
        warmup_script = """
        $ProgressPreference = "SilentlyContinue"
        
        # Check if module is available
        $moduleAvailable = Get-Module -ListAvailable BurntToast
        if (-not $moduleAvailable) {
            Write-Output "BurntToast module is not available"
            exit 1
        }
        
        # Load the module and preload classes
        Import-Module BurntToast -DisableNameChecking -Force
        
        # Pre-load some .NET classes
        $null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
        $null = [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime]
        
        # Load the AppID
        New-BTAppId -AppId "AYON.ToastNotify" -AppDisplayName "AYON ToastNotify" -ErrorAction SilentlyContinue
        
        Write-Output "Warmup completed successfully"
        """
        
        startupinfo = _create_hidden_startupinfo()
        result = subprocess.run(
            [powershell_path, "-NoProfile", "-Command", warmup_script],
            startupinfo=startupinfo,
            capture_output=True,
            text=True,
            check=False
        )
        
        if "Warmup completed successfully" in result.stdout:
            log.info("PowerShell session warm-up complete")
        else:
            log.warning(f"PowerShell warm-up returned unexpected output: {result.stdout}")
            
    except Exception as e:
        log.debug(f"PowerShell warm-up failed: {e}")