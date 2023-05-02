# PyWNP
A Python library to communicate with the [WebNowPlaying-Redux](https://github.com/keifufu/WebNowPlaying-Redux) browser extension.

Refer to [this](https://github.com/keifufu/WebNowPlaying-Redux/blob/main/CreatingAdapters.md) if you want to create or submit your own adapter.

## Installing
Install via pip: `pip install pywnp`

## Usage
```py
from pywnp import WNPRedux
import time

# Custom logger, type can be 'Error', 'Debug' or 'Warning'
def logger(type, message):
  print(f'{type}: {message}')

# Start WNP, providing a websocket port, webserver port, version number and a logger
WNPRedux.start(1234, 1235, '1.0.0', logger)

# Write the current title to the console and pause/unpause the video for 30 seconds
for i in range(30):
  print(WNPRedux.media_info.title)
  # You don't need to check for `supports_play_pause`, but it's good to know about.
  if WNPRedux.media_info.controls.supports_play_pause:
    WNPRedux.media_info.controls.try_toggle_play_pause()
  time.sleep(1)

# Stop WNP
WNPRedux.stop()
```

---
### `WNPRedux.start(wsPort, webPort, version, logger, listenAddress = '127.0.0.1')`
Starts WNP if it isn't already started.  
`wsPort` Port used by the websocket  
`webPort` Port used by the webserver (used to serve cover files over http)  
These ports should _not_ be used by other adapters already, or interfere with any other programs.  
`version` has to be 'x.x.x'.

---
### `WNPRedux.is_started`
Whether WNPRedux is started or not.

---
### `WNPRedux.is_using_native_apis`
Whether WNPRedux is pulling info from native APIs.  
This is read-only, the actual value is set by the user.  
It's toggled in the browser extensions settings panel.  
Read more about it [here](https://github.com/keifufu/WebNowPlaying-Redux/blob/main/NativeAPIs.md).

---
### `WNPRedux.log(type, message)`
Calls the `logger` provided in `WNPRedux.start()`  

---
### `WNPRedux.stop()`
Stops WNP if it's started.

---
### `WNPRedux.clients`
Number of clients currently connected.

# TODO: update this table
---
### `WNPRedux.media_info`
Information about the currently active media.
Name | Default | Description
--- | --- | ---
`controls` | '' | Instance of MediaControls (Read below this table)
`player_name` | '' | Current player, e.g. YouTube, Spotify, etc.
`state` | 'STOPPED' | Current state of the player ('STOPPED', 'PLAYING', 'PAUSED') 
`title` | '' | Title
`artist` | '' | Artist
`album` | '' | Album
`cover_url` | '' | URL to the cover image
`duration` | '0:00' | Duration in (hh):mm:ss (Hours are optional)
`duration_seconds` | 0 | Duration in seconds
`position` | '0:00' | Position in (hh):mm:ss (Hours are optional)
`position_seconds` | 0 | Position in seconds
`position_percent` | 0.0 | Position in percent
`volume` | 100 | Volume from 1-100
`rating` | 0 | Rating from 0-5; Thumbs Up = 5; Thumbs Down = 1; Unrated = 0;
`repeat_mode` | 'NONE' | Current repeat mode ('NONE', 'ONE', 'ALL')
`shuffle_active` | False | If shuffle is enabled

---
### MediaControls
Used in `WNPRedux.media_info.controls`
Name  | Description
--- | ---
`supports_play_pause` | If the current player supports play_pause
`supports_skip_previous` | If the current player supports skip_previous
`supports_skip_next` | If the current player supports skip_next
`supports_set_position` | If the current player supports set_position
`supports_set_volume` | If the current player supports set_volume
`supports_toggle_repeat_mode` | If the current player supports toggle_repeat_mode
`supports_toggle_shuffle_active` | If the current player supports toggle_shuffle_active
`supports_set_rating` | If the current player supports set_rating
`rating_system` | 'NONE' or 'LIKE_DISLIKE' or 'LIKE' or 'SCALE' (SCALE is 0-5)
`try_play()` | Tries to play the current media
`try_pause()` | Tries to pause the current media
`try_toggle_play_pause()` | Tries to play/pause the current media
`try_skip_previous()` | Try to skip to the previous media/section
`try_skip_next()` | Try to skip to the next media/section
`try_set_position_seconds(seconds)` | Try to set the medias playback progress in seconds
`try_revert_position_seconds(seconds)` | Try to revert the medias playback progress by x seconds
`try_forward_position_seconds(seconds)` | Try to forward the medias playback progress by x seconds
`try_set_position_percent(percent)` | Try to set the medias playback progress in percent
`try_revert_position_percent(percent)` | Try to revert the medias playback progress by x percent
`try_forward_position_percent(percent)` | Try to forward the medias playback progress by x percent
`try_set_volume(volume)` | Try to set the medias volume from 1-100
`try_toggle_repeat_mode()` | Try to toggle through repeat modes
`try_toggle_shuffle_active()` | Try to toggle shuffle mode
`try_set_rating(rating)` | Sites with a binary rating system fall back to: 0 = None; 1 = Thumbs Down; 5 = Thumbs Up