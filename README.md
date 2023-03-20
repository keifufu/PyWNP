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

# Start the WebSocket, providing a port, version number and a logger
WNPRedux.Initialize(1234, '1.0.0', logger)

# Write the current title to the console and pause/unpause the video for 30 seconds
for i in range (30):
  print(WNPRedux.mediaInfo.Title)
  WNPRedux.mediaEvents.TogglePlaying()
  time.sleep(1)

# Close the WebSocket
WNPRedux.Close()
```

---
### `WNPRedux.Initialize(port, version, logger)`
Opens the WebSocket if it isn't already opened.  
`port` should _not_ be used by other adapters already, or interfere with any other programs.  
`version` has to be "x.x.x".

---
### `WNPRedux.Log(type, message)`
Calls the `logger` provided in `WNPRedux.Initialize()`  

---
### `WNPRedux.Close()`
Closes the WebSocket if it's opened.

---
### `WNPRedux.clients`
A set of connected clients, useful with `len(WNPRedux.clients)` to see if there are any active connections.  

---
### `WNPRedux.mediaInfo`
Information about the currently active media.
Name | Default | Description
--- | --- | ---
`Player` | "" | Current player, e.g. YouTube, Spotify, etc.
`State` | STOPPED | Current state of the player (STOPPED, PLAYING, PAUSED) 
`Title` | "" | Title
`Artist` | "" | Artist
`Album` | "" | Album
`CoverUrl` | "" | URL to the cover image
`Duration` | "0:00" | Duration in (hh):mm:ss (Hours are optional)
`DurationSeconds` | 0 | Duration in seconds
`Position` | "0:00" | Position in (hh):mm:ss (Hours are optional)
`PositionSeconds` | 0 | Position in seconds
`PositionPercent` | 0.0 | Position in percent
`Volume` | 100 | Volume from 1-100
`Rating` | 0 | Rating from 0-5; Thumbs Up = 5; Thumbs Down = 1; Unrated = 0;
`RepeatState` | NONE | Current repeat state (NONE, ONE, ALL)
`Shuffle` | false | If shuffle is enabled

---
### `WNPRedux.mediaEvents`
Events to interact with the currently active media.  
This isn't guaranteed to always work, since e.g. Spotify has no "dislike" button,  
skip buttons might be disabled in certain scenarios, etc.
Name  | Description
--- | ---
`TogglePlaying()` | Pauses / Unpauses the media
`Next()` | Skips to the next media/section
`Previous()` | Skips to the previous media/section
`SetPositionSeconds(seconds)` | Sets the medias playback progress in seconds
`RevertPositionSeconds(seconds)` | Reverts the medias playback progress by x seconds
`ForwardPositionSeconds(seconds)` | Forwards the medias playback progress by x seconds
`SetPositionPercent(percent)` | Sets the medias playback progress in percent
`RevertPositionPercent(percent)` | Reverts the medias playback progress by x percent
`ForwardPositionPercent(percent)` | Forwards the medias playback progress by x percent
`SetVolume(volume)` | Set the medias volume from 1-100
`ToggleRepeat()` | Toggles through repeat modes
`ToggleShuffle()` | Toggles shuffle mode
`ToggleThumbsUp()` | Toggles thumbs up or similar
`ToggleThumbsDown()` | Toggles thumbs down or similar
`SetRating(rating)` | Sites with a binary rating system fall back to: 0 = None; 1 = Thumbs Down; 5 = Thumbs Up