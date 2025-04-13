import os
import sys
import time
import shutil
import platform
import tempfile
import threading
import plistlib
import subprocess
from pathlib import Path

_installation_lock = threading.Lock()
_installation_completed = False
_installation_result = None
_installation_in_progress = False  # This was missing

from . import AYON_TOASTNOTIFY_ROOT
from .api.logger import log

def _fix_alerter_permissions(app_path):
    """Fix permissions and security settings for the alerter app bundle."""
    try:
        alerter_exe = app_path / "Contents" / "MacOS" / "alerter"
        
        if not os.path.exists(app_path):
            log.error(f"Cannot fix permissions: App bundle not found at {app_path}")
            return False
            
        if not os.path.exists(alerter_exe):
            log.error(f"Cannot fix permissions: Executable not found at {alerter_exe}")
            return False
        
        # Set executable permissions
        try:
            os.chmod(alerter_exe, 0o755)
            log.debug(f"Set executable permissions on {alerter_exe}")
        except Exception as e:
            log.error(f"Could not set executable permissions: {e}")
        
        # Remove quarantine attributes - be more thorough
        try:
            # Remove quarantine from the entire app bundle
            subprocess.run(['xattr', '-dr', 'com.apple.quarantine', str(app_path)],
                          check=False, capture_output=True)
            
            # Also directly remove from the executable itself
            subprocess.run(['xattr', '-d', 'com.apple.quarantine', str(alerter_exe)],
                         check=False, capture_output=True)
                         
            # Remove all extended attributes to be thorough
            subprocess.run(['xattr', '-cr', str(app_path)],
                         check=False, capture_output=True)
                         
            # Remove any potential ACLs
            subprocess.run(['chmod', '-R', '-N', str(app_path)],
                         check=False, capture_output=True)
                         
            log.debug("Removed quarantine attributes and extended attributes")
        except Exception as e:
            log.warning(f"Could not remove quarantine attributes: {e}")
        
        # Fix permissions on the entire bundle - be more aggressive
        try:
            # Make sure the bundle and all contents are readable/executable
            subprocess.run(['chmod', '-R', '755', str(app_path)], check=False)
            
            # Ensure the main executable is properly set
            subprocess.run(['chmod', '755', str(alerter_exe)], check=False)
            
            # Ensure the user owns the files
            user = os.environ.get('USER', 'root')
            subprocess.run(['chown', '-R', user, str(app_path)], check=False)
            
            log.debug("Set permissions on app bundle")
        except Exception as e:
            log.warning(f"Could not set permissions on app bundle: {e}")
        
        # Try to pre-authorize the app with macOS security
        try:
            # This basically "touches" the app, which can help with first-run issues
            subprocess.run(['open', '-n', str(app_path), '--args', '-help'],
                          check=False, timeout=1)
        except subprocess.TimeoutExpired:
            # This is expected - we just want to trigger the security dialog
            pass
        except Exception as e:
            log.warning(f"Could not pre-authorize app: {e}")
        
        return True
        
    except Exception as e:
        log.error(f"Error fixing alerter permissions: {e}")
        return False

def _create_alerter_app_bundle(dest_dir):
    """Create a properly structured Alerter.app bundle with proper signing."""
    try:
        # Clean up any existing installation first
        app_path = dest_dir / "Alerter.app"
        if app_path.exists():
            log.info(f"Removing existing Alerter.app at {app_path}")
            shutil.rmtree(app_path, ignore_errors=True)
        
        # Determine Mac architecture
        is_apple_silicon = False
        try:
            arch = subprocess.check_output(['uname', '-m']).decode().strip()
            log.debug(f"Detected architecture: {arch}")
            is_apple_silicon = arch == 'arm64'
        except Exception as e:
            log.warning(f"Could not detect architecture, assuming Intel: {e}")
        
        # Source binary - either architecture-specific or universal
        source_binary = AYON_TOASTNOTIFY_ROOT / "vendor" / "alerter" / "alerter"
        if not source_binary.exists():
            # Fall back to architecture-specific binaries
            if is_apple_silicon:
                source_binary = AYON_TOASTNOTIFY_ROOT / "vendor" / "alerter" / "alerter_arm64"
            else:
                source_binary = AYON_TOASTNOTIFY_ROOT / "vendor" / "alerter" / "alerter_amd64"
        
        # Get path to the Info.plist
        vendor_dir = AYON_TOASTNOTIFY_ROOT / "vendor" / "alerter"
        info_plist_source = vendor_dir / "Info.plist"
        
        log.debug(f"Checking source binary at: {source_binary}")
        log.debug(f"Source binary exists: {source_binary.exists()}")
        log.debug(f"Info.plist source exists: {info_plist_source.exists()}")
        
        if not source_binary.exists():
            log.error(f"Source binary not found at {source_binary}")
            return None
            
        # Create app bundle structure
        contents_dir = app_path / "Contents"
        macos_dir = contents_dir / "MacOS"
        resources_dir = contents_dir / "Resources"
        
        # Create directories
        for d in (app_path, contents_dir, macos_dir, resources_dir):
            d.mkdir(parents=True, exist_ok=True)
        
        # Copy and set up binary
        alerter_path = macos_dir / "alerter"
        shutil.copy2(source_binary, alerter_path)
        os.chmod(alerter_path, 0o755)
        
        # Create Info.plist - simplified logic
        info_plist_path = contents_dir / "Info.plist"
        if info_plist_source.exists():
            # Just copy the fixed plist we already have
            shutil.copy2(info_plist_source, info_plist_path)
            log.debug(f"Copied Info.plist from {info_plist_source}")
        else:
            # This should rarely happen if the vendor folder is set up correctly
            log.warning("Info.plist source not found, creating a default one")
            with open(info_plist_path, 'w') as f:
                f.write('''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>alerter</string>
    <key>CFBundleIconFile</key>
    <string>Terminal</string>
    <key>CFBundleIdentifier</key>
    <string>com.ayon.alerter</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>Alerter</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.1</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.14</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsArbitraryLoads</key>
        <true/>
    </dict>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © 2023 AYON Framework</string>
    <key>NSUserNotificationAlertStyle</key>
    <string>alert</string>
</dict>
</plist>''')
        
        # Create PkgInfo
        with open(contents_dir / "PkgInfo", 'w') as f:
            f.write("APPL????")
        
        # Fix permissions on the entire bundle
        log.debug("Setting permissions on app bundle")
        subprocess.run(['chmod', '-R', '755', str(app_path)], check=False)
        
        # Remove quarantine attributes
        log.debug("Removing quarantine attributes")
        subprocess.run(['xattr', '-rd', 'com.apple.quarantine', str(app_path)], check=False)
        subprocess.run(['xattr', '-rc', str(app_path)], check=False)
        
        # Try to sign the app with ad-hoc signature
        log.debug("Attempting to ad-hoc sign the app")
        try:
            subprocess.run(['codesign', '--force', '--deep', '--sign', '-', str(app_path)], 
                          check=False, capture_output=True)
            log.debug("Ad-hoc signing completed")
        except Exception as e:
            log.warning(f"Could not sign app bundle (will still try to use it): {e}")
        
        log.info(f"Successfully created alerter app bundle at {alerter_path}")
        return alerter_path
    
    except Exception as e:
        log.error(f"Error creating alerter app bundle: {e}")
        return None

def _ensure_alerter_available(force_reinstall=False):
    """Ensure alerter is available as a properly structured app bundle."""
    global _installation_completed, _installation_result, _installation_in_progress
    
    # Skip if not on macOS
    if platform.system() != "Darwin":
        return None
    
    # Force reinstall if requested
    if force_reinstall:
        _installation_completed = False
        _installation_result = None
    
    # Check if installation is already completed
    with _installation_lock:
        if _installation_completed and not force_reinstall:
            return _installation_result
    
    # Look for existing installation
    app_dir = Path.home() / ".ayon" / "apps"
    app_path = app_dir / "Alerter.app"
    alerter_exe = app_path / "Contents" / "MacOS" / "alerter"
    
    # If it exists and is executable, use it (unless force_reinstall)
    if not force_reinstall and alerter_exe.exists() and os.access(alerter_exe, os.X_OK):
        log.debug(f"Found existing alerter app bundle at {alerter_exe}")
        
        # Fix permissions if needed
        _fix_alerter_permissions(app_path)
        
        with _installation_lock:
            _installation_completed = True
            _installation_result = str(alerter_exe)
        return str(alerter_exe)
    
    # Create app directory if it doesn't exist
    app_dir.mkdir(parents=True, exist_ok=True)
    
    # If path exists but we're reinstalling, remove it
    if app_path.exists():
        log.debug(f"Removing existing app bundle for reinstallation at {app_path}")
        try:
            shutil.rmtree(app_path)
        except Exception as e:
            log.error(f"Failed to remove existing app bundle: {e}")
    
    # Create the app bundle
    with _installation_lock:
        _installation_in_progress = True
    
    try:
        alerter_exe = _create_alerter_app_bundle(app_dir)
        
        if alerter_exe:
            log.info(f"Successfully installed alerter at {alerter_exe}")
            with _installation_lock:
                _installation_completed = True
                _installation_result = str(alerter_exe)
                _installation_in_progress = False
            
            # After successful installation, guide user to set notification preferences
            result = subprocess.run([
                "osascript", "-e", 
                'display dialog "Alerter has been installed. Would you like to configure notification settings now?" buttons {"Not Now", "Configure"} default button "Configure" with title "Notification Setup"'
            ], capture_output=True, text=True)
            
            # If the user clicked "Configure", open the settings
            if result.stdout.strip() == "button returned:Configure":
                # Open notification settings
                subprocess.run([
                    "open", "x-apple.systempreferences:com.apple.preference.notifications"
                ])
            
            return str(alerter_exe)
        else:
            log.error("Failed to create alerter app bundle")
            with _installation_lock:
                _installation_completed = True
                _installation_result = None
                _installation_in_progress = False
            return None
    except Exception as e:
        log.error(f"Error in alerter installation: {e}")
        with _installation_lock:
            _installation_in_progress = False
        return None

def force_reinstall_alerter():
    """Force reinstallation of alerter app bundle."""
    global _installation_completed, _installation_result, _installation_in_progress
    
    log.info("Forcing reinstallation of alerter")
    
    # Reset installation status
    with _installation_lock:
        _installation_completed = False
        _installation_result = None
        _installation_in_progress = False
    
    # Delete existing installation
    app_dir = Path.home() / ".ayon" / "apps"
    app_path = app_dir / "Alerter.app"
    
    if app_path.exists():
        try:
            shutil.rmtree(app_path)
            log.info(f"Removed existing Alerter.app at {app_path}")
        except Exception as e:
            log.error(f"Error removing existing installation: {e}")
    
    # Run the installation
    return _ensure_alerter_available(force_reinstall=True)

def open_notification_settings():
    """Open the macOS notification settings panel."""
    if platform.system() != "Darwin":
        log.warning("This function is only applicable on macOS")
        return False
    
    try:
        # Open the Notifications preference pane
        subprocess.run([
            "open", "x-apple.systempreferences:com.apple.preference.notifications"
        ])
        log.info("Opened notification settings panel")
        return True
    except Exception as e:
        log.error(f"Error opening notification settings: {e}")
        return False

def configure_alerter_notifications():
    """Guide user through configuring alerter notification settings."""
    if platform.system() != "Darwin":
        log.warning("This function is only applicable on macOS")
        return False
        
    try:
        # First ensure alerter is installed
        alerter_path = _ensure_alerter_available()
        
        if not alerter_path:
            log.error("Cannot configure notifications - alerter is not installed")
            return False
            
        # Show a prompt to the user
        result = subprocess.run([
            "osascript", "-e", 
            'display dialog "Would you like to configure Alerter notification settings now? This will help ensure notifications appear properly." buttons {"Not Now", "Configure"} default button "Configure" with title "AYON Notification Setup"'
        ], capture_output=True, text=True)
        
        if "button returned:Configure" in result.stdout:
            # Open notification settings
            return open_notification_settings()
        else:
            log.info("User chose not to configure notification settings")
            return False
    except Exception as e:
        log.error(f"Error during notification configuration: {e}")
        return False

def install_alerter(settings, async_install=True):
    """Install alerter for macOS toast notifications."""
    global _installation_in_progress
    
    if platform.system() != "Darwin":
        return None
    
    if _installation_in_progress:
        log.debug("Alerter installation already in progress, skipping")
        return None
    
    if async_install:
        # Install in a separate thread to not block startup
        threading.Thread(
            target=_ensure_alerter_available,
            args=(False,),
            daemon=True
        ).start()
        return None
    else:
        # Install synchronously
        return _ensure_alerter_available(False)