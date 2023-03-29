import asyncio
from websockets import serve
from datetime import datetime
from threading import Thread

class MediaInfo:
  def __init__(self):
    self._Title = ''
    self._State = 'STOPPED'
    self._Volume = 0
    self.WebSocketID = ''
    self.Player = ''
    self.Artist = ''
    self.Album = ''
    self.CoverUrl = ''
    self.Duration = '0:00'
    self.DurationSeconds = 0
    self.Position = '0:00'
    self.PositionSeconds = 0
    self.PositionPercent = 0
    self.Volume = 100
    self.Rating = 0
    self.RepeatState = 'NONE'
    self.Shuffle = False
    self.Timestamp = 0
  
  @property
  def State(self):
    return self._State
  
  @State.setter
  def State(self, value):
    self._State = value
    self.Timestamp = datetime.now().timestamp()
  
  @property
  def Title(self):
    return self._Title
  
  @Title.setter
  def Title(self, value):
    self._Title = value
    if value != '':
      self.Timestamp = datetime.now().timestamp()
    else:
      self.Timestamp = 0
  
  @property
  def Volume(self):
    return self._Volume
  
  @Volume.setter
  def Volume(self, value):
    self._Volume = value
    self.Timestamp = datetime.now().timestamp()

class MediaEvents:
  def TogglePlaying(self):
    WNPRedux._SendMessage('TOGGLE_PLAYING')

  def Next(self):
    WNPRedux._SendMessage('NEXT')

  def Previous(self):
    WNPRedux._SendMessage('PREVIOUS')

  def SetPositionSeconds(self, seconds):
    positionInSeconds = seconds
    if positionInSeconds < 0:
      positionInSeconds = 0
    if positionInSeconds > WNPRedux.mediaInfo.DurationSeconds:
      positionInSeconds = WNPRedux.mediaInfo.DurationSeconds
    # DurationSeconds or 1 is to prevent division by zero if the duration is unknown
    positionInPercent = positionInSeconds / (WNPRedux.mediaInfo.DurationSeconds or 1)
    # This makes sure it always gives us 0.0, not 0,0 (dot instead of comma, regardless of localization)
    positionInPercentString = str(positionInPercent)

    WNPRedux._SendMessage(f'SET_POSITION {positionInSeconds}:{positionInPercentString}')

  def RevertPositionSeconds(self, seconds):
    self.SetPositionSeconds(WNPRedux.mediaInfo.PositionSeconds - seconds)

  def ForwardPositionSeconds(self, seconds):
    self.SetPositionSeconds(WNPRedux.mediaInfo.PositionSeconds + seconds)

  def SetPositionPercent(self, percent):
    seconds = round((percent / 100) * WNPRedux.mediaInfo.DurationSeconds)
    self.SetPositionSeconds(seconds)

  def RevertPositionPercent(self, percent):
    seconds = round((percent / 100) * WNPRedux.mediaInfo.DurationSeconds)
    self.SetPositionSeconds(WNPRedux.mediaInfo.PositionSeconds - seconds)

  def ForwardPositionPercent(self, percent):
    seconds = round((percent / 100) * WNPRedux.mediaInfo.DurationSeconds)
    self.SetPositionSeconds(WNPRedux.mediaInfo.PositionSeconds + seconds)
  
  def SetVolume(self, volume):
    newVolume = volume
    if volume < 0:
        newVolume = 0
    if volume > 100:
        newVolume = 100
    WNPRedux._SendMessage(f'SET_VOLUME {newVolume}')

  def ToggleRepeat(self):
    WNPRedux._SendMessage('TOGGLE_REPEAT}')

  def ToggleShuffle(self):
    WNPRedux._SendMessage('TOGGLE_SHUFFLE')

  def ToggleThumbsUp(self):
    WNPRedux._SendMessage('TOGGLE_THUMBS_UP')

  def ToggleThumbsDown(self):
    WNPRedux._SendMessage('TOGGLE_THUMBS_DOWN')

  def SetRating(self, rating):
    WNPRedux._SendMessage(f'SET_RATING {rating}')

class WNPRedux:
  isInitialized = False
  mediaInfo = MediaInfo()
  mediaEvents = MediaEvents()
  _mediaInfoDictionary = list()
  _server = None
  clients = set()
  _version = '0.0.0'
  _future = None
  _logger = None

  def Initialize(port, version, logger, loopback = '127.0.0.1'):
    if WNPRedux.isInitialized: return
    WNPRedux.isInitialized = True
    WNPRedux.mediaInfo = MediaInfo()
    WNPRedux._mediaInfoDictionary = list()
    WNPRedux.clients = set()
    WNPRedux._version = version
    WNPRedux._logger = logger
    Thread(target = WNPRedux._threaded_start, args = (port, loopback,), daemon=True).start()

  def _threaded_start(port, loopback):
    asyncio.run(WNPRedux._start(port, loopback))

  async def _start(port, loopback):
    if WNPRedux._server != None: return
    WNPRedux._server = serve(WNPRedux._onConnect, loopback, port)
    WNPRedux._future = asyncio.Future()
    async with WNPRedux._server:
      await WNPRedux._future

  def _SendMessage(message):
    for client in WNPRedux.clients:
      if client.id == WNPRedux.mediaInfo.WebSocketID:
        asyncio.run(client.send(message))
        break

  def Log(type, message):
    if WNPRedux._logger == None: return
    WNPRedux._logger(type, message)

  def Close():
    if not WNPRedux.isInitialized: return
    WNPRedux.isInitialized = False
    WNPRedux._future.set_result(None)
    WNPRedux._server = None
    WNPRedux._future = None
    pass

  async def _onConnect(websocket):
    WNPRedux.clients.add(websocket)
    websocket.id = str(datetime.now())
    await websocket.send(f'ADAPTER_VERSION {WNPRedux._version};WNPRLIB_REVISION 1')
    try:
      async for message in websocket:
        messageType = message[:message.index(' ')].upper()
        info = message[message.index(' ') + 1:]

        currentMediaInfo = MediaInfo()
        found = False
        for mediaInfo in WNPRedux._mediaInfoDictionary:
          if mediaInfo.WebSocketID == websocket.id:
            currentMediaInfo = mediaInfo
            found = True
            break
          
        currentMediaInfo.WebSocketID = websocket.id

        if not found:
          WNPRedux._mediaInfoDictionary.append(currentMediaInfo)

        if messageType == 'PLAYER':
          currentMediaInfo.Player = info
        elif messageType == 'STATE':
          currentMediaInfo.State = info
        elif messageType == 'TITLE':
          currentMediaInfo.Title = info
        elif messageType == 'ARTIST':
          currentMediaInfo.Artist = info
        elif messageType == 'ALBUM':
          currentMediaInfo.Album = info
        elif messageType == 'COVER':
          currentMediaInfo.CoverUrl = info
        elif messageType == 'DURATION':
          currentMediaInfo.Duration = info
          currentMediaInfo.DurationSeconds = WNPRedux._ConvertTimeToSeconds(info)
          # I guess set PositionPercent to 0, because if duration changes, a new video is playing
          currentMediaInfo.PositionPercent = 0
        elif messageType == 'POSITION':
          currentMediaInfo.Position = info
          currentMediaInfo.PositionSeconds = WNPRedux._ConvertTimeToSeconds(info)

          if (currentMediaInfo.DurationSeconds > 0):
            currentMediaInfo.PositionPercent = currentMediaInfo.PositionSeconds / currentMediaInfo.DurationSeconds * 100
          else:
            currentMediaInfo.PositionPercent = 100
        elif messageType == 'VOLUME':
          currentMediaInfo.Volume = int(info)
        elif messageType == 'RATING':
          currentMediaInfo.Rating = int(info)
        elif messageType == 'REPEAT':
          currentMediaInfo.RepeatState = info
        elif messageType == 'SHUFFLE':
          currentMediaInfo.Shuffle = info.upper() == 'TRUE'
        elif messageType == 'ERROR':
          WNPRedux.Log('Error', info)
        elif messageType == 'ERRORDEBUG':
          WNPRedux.Log('Debug', info)
        else:
          WNPRedux.Log('Warning', f'Unknown message type: {messageType}')
        
        if messageType != 'POSITION' and currentMediaInfo.Title != '':
          WNPRedux._UpdateMediaInfo()
    finally:
      WNPRedux.clients.remove(websocket)
      for mediaInfo in WNPRedux._mediaInfoDictionary:
        if mediaInfo.WebSocketID == websocket.id:
          WNPRedux._mediaInfoDictionary.remove(mediaInfo)
          break
      WNPRedux._UpdateMediaInfo()
  
  def _UpdateMediaInfo():
    WNPRedux._mediaInfoDictionary = sorted(WNPRedux._mediaInfoDictionary, key=lambda x: x.Timestamp, reverse=True)
    suitableMatch = False

    for mediaInfo in WNPRedux._mediaInfoDictionary:
      if mediaInfo.State == 'PLAYING' and mediaInfo.Volume > 0:
        WNPRedux.mediaInfo = mediaInfo
        suitableMatch = True
        break
    
    if not suitableMatch:
      if len(WNPRedux._mediaInfoDictionary) > 0:
        WNPRedux.mediaInfo = WNPRedux._mediaInfoDictionary[0]
      else:
        WNPRedux.mediaInfo = MediaInfo()

  def _ConvertTimeToSeconds(time):
    dur_arr = time.split(':')

    # Duration will always have seconds and minutes, but hours are optional
    try:
      dur_sec = int(dur_arr[-1])
      dur_min = int(dur_arr[-2]) * 60 if len(dur_arr) > 1 else 0
      dur_hour = int(dur_arr[-3]) * 60 * 60 if len(dur_arr) > 2 else 0
      return dur_hour + dur_min + dur_sec
    except ValueError:
      return 0