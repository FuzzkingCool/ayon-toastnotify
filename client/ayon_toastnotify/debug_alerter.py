import os
import sys
import subprocess
import platform
from pathlib import Path

def debug_alerter():
    """Debug function to check alerter functionality directly."""
    alerter_path = Path.home() / ".ayon" / "apps" / "Alerter.app" / "Contents" / "MacOS" / "alerter"
    
    print(f"Checking if alerter exists at {alerter_path}...")
    if os.path.exists(alerter_path):
        print(f"SUCCESS: Alerter binary found at {alerter_path}")
        if os.access(alerter_path, os.X_OK):
            print("SUCCESS: Alerter binary is executable")
        else:
            print("ERROR: Alerter binary is not executable")
    else:
        print(f"ERROR: Alerter binary not found at {alerter_path}")
        return
    
    print("\nTesting alerter binary directly...")
    cmd = [str(alerter_path), "-help"]
    print(f"Running command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f"Return code: {result.returncode}")
        print(f"Output: {result.stdout}")
        print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"ERROR: Exception executing alerter: {e}")
    
    print("\nSending direct test notification...")
    cmd = [str(alerter_path), "-title", "Test", "-message", "Direct test message", "-timeout", "5"]
    print(f"Running command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f"Return code: {result.returncode}")
        print(f"Output: {result.stdout}")
        print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"ERROR: Exception sending notification: {e}")
    
    print("\nChecking app bundle structure...")
    app_path = Path.home() / ".ayon" / "apps" / "Alerter.app"
    print(f"App bundle path: {app_path}")
    
    info_plist = app_path / "Contents" / "Info.plist"
    print(f"Info.plist exists: {os.path.exists(info_plist)}")
    
    pkg_info = app_path / "Contents" / "PkgInfo"
    print(f"PkgInfo exists: {os.path.exists(pkg_info)}")
    
    print("\nApp bundle permissions:")
    try:
        subprocess.run(["ls", "-la", str(app_path)], check=False)
    except Exception as e:
        print(f"ERROR: Failed to get permissions: {e}")
    
    # Try using terminal-notifier as an alternative
    print("\nTesting terminal-notifier:")
    try:
        result = subprocess.run(["which", "terminal-notifier"], capture_output=True, text=True)
        if result.returncode == 0:
            terminal_notifier_path = result.stdout.strip()
            print(f"terminal-notifier found at: {terminal_notifier_path}")
            
            # Test notification with terminal-notifier
            test_cmd = [terminal_notifier_path, "-title", "Test", "-message", "Terminal Notifier Test"]
            subprocess.run(test_cmd, check=False)
            print("Terminal-notifier notification sent")
        else:
            print("terminal-notifier not found")
    except Exception as e:
        print(f"ERROR: Failed to test terminal-notifier: {e}")

def run_direct_test():
    """Run a direct test of the alerter binary."""
    alerter_path = Path.home() / ".ayon" / "apps" / "Alerter.app" / "Contents" / "MacOS" / "alerter"
    
    if not os.path.exists(alerter_path):
        print(f"ERROR: Alerter binary not found at {alerter_path}")
        return
    
    print(f"Alerter binary found at {alerter_path}")
    
    # Try running with direct command
    try:
        cmd = [str(alerter_path), "-title", "Direct Test", "-message", "Testing direct command", "-timeout", "5"]
        print(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        print(f"Return code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        
        if result.returncode == 0:
            print("SUCCESS: Direct command worked!")
        else:
            print(f"ERROR: Direct command failed with code {result.returncode}")
    except Exception as e:
        print(f"ERROR: Exception running direct command: {e}")

if __name__ == "__main__":
    debug_alerter()
    run_direct_test()