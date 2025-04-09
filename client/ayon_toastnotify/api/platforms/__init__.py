import platform

def get_platform_handler():
    """Get the appropriate platform handler for the current OS"""
    system = platform.system()
    
    if system == "Windows":
        from .windows import ToastNotifyWindowsPlatform
        return ToastNotifyWindowsPlatform
    elif system == "Darwin":
        from .macos import ToastNotifyMacOSPlatform
        return ToastNotifyMacOSPlatform
    elif system == "Linux":
        from .linux_generic import ToastNotifyLinuxPlatform
        return ToastNotifyLinuxPlatform
    else:
        raise RuntimeError(f"Unsupported platform: {system}")