# ayon-toastnotify

A simple AYON addon providing a cross-platform api to give toast notifications on user systems.


# ToastNotify API

## Basic Usage (Cross-Platform)

```python
from ayon_toastnotify import send_notification

# Simple notification
send_notification("Document Saved", "Your document was saved successfully")

```

# With an icon

```python
from ayon_toastnotify import send_notification
send_notification("Download Complete", "File ready to use", icon="path/to/icon.png")
```

# With action buttons

```python
from ayon_toastnotify import send_notification
send_notification( 
   "New Message",
   "You received a new message from John",
   actions=[
	{"id": "view", "text": "View"},
        {"id": "dismiss", "text": "Dismiss"}  
])
```

# Windows-specific with BurntToast features

```python
from ayon_toastnotify import send_notification

send_notification(
	"Task Complete",
   	"Long-running process finished",
	actions=[{"id": "view", "text": "View Results"}],
   	platform_options={"windows": {"sound": "Alarm2",
				      "app_id": "MyApplication",
			              "unique_identifier": "task-123",
			              "suppress_popup": False,
			              "hero_image": "C:/path/to/hero.jpg"}}
)
```


# macOS-specific features

```python
from ayon_toastnotify import send_notification

send_notification(
    "Download Complete",
    "Your file is ready",
    platform_options={"macos": {"subtitle": "From cloud storage",
	              "sound_name": "Purr"}}
)
```
