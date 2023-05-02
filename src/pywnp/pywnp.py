from datetime import datetime
from threading import Thread
import concurrent.futures
from sys import platform
import websockets
import asyncio
import json
import math
import os

pool = concurrent.futures.ThreadPoolExecutor()

def pad(num, size): return str(num).rjust(size, '0')
def time_in_seconds_to_string(time_in_seconds: int):
  try:
    if time_in_seconds == None: return '0:00'
    time_in_minutes = math.floor(time_in_seconds / 60)
    if time_in_minutes < 60:
      return str(time_in_minutes) + ':' + str(pad(math.floor(time_in_seconds % 60), 2))

    return str(math.floor(time_in_minutes / 60)) + ':' + str(pad(math.floor(time_in_minutes % 60), 2)) + ':' + str(pad(math.floor(time_in_seconds % 60), 2))
  except:
    return '0:00'

is_windows = platform.startswith('win')
if is_windows:
  from winsdk.windows.media.control import\
    GlobalSystemMediaTransportControlsSession as Session,\
    GlobalSystemMediaTransportControlsSessionManager as SessionManager
  from winsdk.windows.storage.streams import \
    DataReader, Buffer, InputStreamOptions, IRandomAccessStreamReference
  import urllib.parse
  import socketserver
  import http.server
  import tempfile
  import random
  import signal

  class WNPWebServer:
    server = None
    thread = None

    def start(host, port):
      if not WNPWebServer.server:
        WNPWebServer.server = socketserver.TCPServer((host, port), WNPWebServerRequestHandler)
        WNPWebServer.thread = Thread(target=WNPWebServer.server.serve_forever)
        WNPWebServer.thread.start()

    def stop():
      if WNPWebServer.server:
        WNPWebServer.server.shutdown()
        WNPWebServer.server.server_close()
        WNPWebServer.thread.join()
        WNPWebServer.server = None
        WNPWebServer.thread = None

  class WNPWebServerRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
      pass

    def do_GET(self):
      if self.path.startswith('/image?'):
        parsed_url = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed_url.query)
        if 'path' in params:
          url = urllib.parse.unquote(params['path'][0])
          if os.path.exists(url):
            if url.endswith('.jpg'):
              with open(url, 'rb') as f:
                self.send_response(200)
                self.send_header('Content-type', 'image/jpeg')
                self.end_headers()
                self.wfile.write(f.read())
            else:
              self.send_error(400, 'File is not an image')
          else:
            self.send_error(404, 'File not found')
        else:
          self.send_error(400, 'Missing path parameter')
      else:
        super().do_GET()

  class WNPWindows:
    is_started = False
    manager: SessionManager = None
    current_session: Session = None
    current_session_changed_token = None
    media_properties_changed_token = None
    playback_info_changed_token = None
    timeline_properties_changed_token = None
    last_title = ''
    _loop = None

    def _get_media_info():
      # Offset of -5 seconds
      current_media_info = MediaInfo(-5)
      found = False
      for media_info in WNPRedux._media_info_dictionary:
        if media_info._id == 'WINDOWS':
          current_media_info = media_info
          found = True
          break
        
      current_media_info._id = 'WINDOWS'
      current_media_info.player_name = 'Windows Media Session'

      if not found:
        WNPRedux._media_info_dictionary.append(current_media_info)

      return current_media_info

    def start():
      if not WNPWindows.is_started:
        WNPWindows.is_started = True
        WNPWebServer.start(WNPRedux.listen_address, WNPRedux.webPort)
        Thread(target = WNPWindows._threaded_start).start()
        
    def _threaded_start():
      WNPWindows._loop = asyncio.new_event_loop()
      WNPWindows._loop.run_until_complete(WNPWindows._start_async())

    async def _start_async():
      WNPWindows.manager = await SessionManager.request_async()
      WNPWindows.current_session_changed(WNPWindows.manager, None)
      WNPWindows.current_session_changed_token = WNPWindows.manager.add_current_session_changed(WNPWindows.current_session_changed)

    def stop():
      if WNPWindows.is_started:
        WNPWindows.is_started = False
        WNPWebServer.stop()
        WNPWindows._loop.stop()

        def close():
          def timeout_handler():
            raise TimeoutError('Function timed out')
          signal.signal(signal.SIGALRM, timeout_handler)
          try:
            if WNPWindows.manager != None:
              WNPWindows.manager.remove_current_session_changed(WNPWindows.current_session_changed_token)
            WNPWindows.manager = None
            if WNPWindows.current_session != None:
              WNPWindows.current_session.remove_media_properties_changed(WNPWindows.media_properties_changed_token)
              WNPWindows.current_session.remove_playback_info_changed(WNPWindows.playback_info_changed_token)
              WNPWindows.current_session.remove_timeline_properties_changed(WNPWindows.timeline_properties_changed_token)
            WNPWindows.current_session = None
            WNPWindows.last_title = ''
          except TimeoutError: pass

        close()

        for media_info in WNPRedux._media_info_dictionary:
          if media_info._id == 'WINDOWS':
            WNPRedux._media_info_dictionary.remove(media_info)
            break
        WNPRedux._update_media_info()
        WNPRedux._update_recipients()

    def current_session_changed(session_manager: SessionManager, e):
      for media_info in WNPRedux._media_info_dictionary:
        if media_info._id == 'WINDOWS':
          WNPRedux._media_info_dictionary.remove(media_info)
          break
      WNPRedux._update_media_info()
      WNPRedux._update_recipients()
      if WNPWindows.current_session != None:
        WNPWindows.current_session.remove_media_properties_changed(WNPWindows.media_properties_changed_token)
        WNPWindows.current_session.remove_playback_info_changed(WNPWindows.playback_info_changed_token)
        WNPWindows.current_session.remove_timeline_properties_changed(WNPWindows.timeline_properties_changed_token)
      WNPWindows.current_session = session_manager.get_current_session()
      if WNPWindows.current_session != None:
        WNPWindows.media_properties_changed(WNPWindows.current_session, None)
        WNPWindows.playback_info_changed(WNPWindows.current_session, None)
        WNPWindows.timeline_properties_changed(WNPWindows.current_session, None)
        WNPWindows.media_properties_changed_token = WNPWindows.current_session.add_media_properties_changed(WNPWindows.media_properties_changed)
        WNPWindows.playback_info_changed_token = WNPWindows.current_session.add_playback_info_changed(WNPWindows.playback_info_changed)
        WNPWindows.timeline_properties_changed_token = WNPWindows.current_session.add_timeline_properties_changed(WNPWindows.timeline_properties_changed)

    def media_properties_changed(session: Session, e):
      info = pool.submit(asyncio.run, WNPWindows.media_properties_changed_coroutine(session)).result()
      if (info == None): return
      media_info = WNPWindows._get_media_info()
      if info.thumbnail == None:
        media_info.cover_url = ''
      elif info.title != WNPWindows.last_title:
        pool.submit(asyncio.run, WNPWindows.write_thumbnail(info.thumbnail))
        WNPWindows.last_title = info.title or ""
      media_info.title = info.title or ""
      media_info.artist = info.artist or ""
      WNPRedux._update_media_info()
      WNPRedux._update_recipients()

    async def media_properties_changed_coroutine(session: Session):
      # Sometimes, we get "The device is not ready". This can easily be replicated by opening foobar2000 while this is running.
      try:
        return await session.try_get_media_properties_async()
      except: pass

    async def write_thumbnail(thumbnail: IRandomAccessStreamReference):
      try:
        # 5MB (5 million byte) buffer - thumbnail unlikely to be larger
        buffer = Buffer(5000000)
        readable_stream = await thumbnail.open_read_async()
        await readable_stream.read_async(buffer, buffer.capacity, InputStreamOptions.READ_AHEAD)
        if buffer.length == 0: return
        buffer_reader = DataReader.from_buffer(buffer)
        byte_buffer = buffer_reader.read_buffer(buffer.length)
        path = f'{tempfile.gettempdir()}\\wnp.jpg'
        with open(path, 'wb+') as fobj:
          fobj.write(bytearray(byte_buffer))
        media_info = WNPWindows._get_media_info()
        p = path.replace('\\', '/')
        media_info.cover_url = f'http://{WNPRedux.listen_address}:{WNPRedux.webPort}/image?path={p}&r={random.randint(0, 999999)}'
      except: pass

    def playback_info_changed(session: Session, e):
      info = session.get_playback_info()
      media_info = WNPWindows._get_media_info()
      media_info.shuffle_active = info.is_shuffle_active or False
      media_info.controls = MediaControls(info.controls.is_play_pause_toggle_enabled, info.controls.is_previous_enabled, info.controls.is_next_enabled, info.controls.is_playback_position_enabled, False, info.controls.is_repeat_enabled, info.controls.is_shuffle_enabled, False, 'None')

      if info.auto_repeat_mode == None:
        media_info.repeat_mode = 'NONE'
      else:
        if info.auto_repeat_mode.value == 0:
          media_info.repeat_mode = 'NONE'
        elif info.auto_repeat_mode.value == 1:
          media_info.repeat_mode = 'ONE'
        elif info.auto_repeat_mode.value == 2:
          media_info.repeat_mode = 'ALL' 

      if info.playback_status == None:
        media_info.state = 'STOPPED'
      elif info.playback_status.value == 4:
        media_info.state = 'PLAYING'
      else:
        media_info.state = 'PAUSED'

      WNPRedux._update_media_info()
      WNPRedux._update_recipients()

    def timeline_properties_changed(session: Session, e):
      info = session.get_timeline_properties()
      media_info = WNPWindows._get_media_info()

      media_info.duration_seconds = info.end_time.seconds
      media_info.duration = time_in_seconds_to_string(media_info.duration_seconds)
      
      media_info.position_seconds = info.position.seconds
      media_info.position = time_in_seconds_to_string(media_info.position_seconds)
      if media_info.duration_seconds > 0:
        media_info.position_percent = (media_info.position_seconds / media_info.duration_seconds) * 100
      else:
        media_info.position_percent = 100
        
      WNPRedux._update_media_info()
      WNPRedux._update_recipients()

class MediaControls:
  def __init__(self, supports_play_pause = False, supports_skip_previous = False, supports_skip_next = False, supports_set_position = False, supports_set_volume = False, supports_toggle_repeat_mode = False, supports_toggle_shuffle_active = False, supports_set_rating = False, rating_system = 'NONE'):
    self.supports_play_pause = supports_play_pause
    self.supports_skip_previous = supports_skip_previous
    self.supports_skip_next = supports_skip_next
    self.supports_set_position = supports_set_position
    self.supports_set_volume = supports_set_volume
    self.supports_toggle_repeat_mode = supports_toggle_repeat_mode
    self.supports_toggle_shuffle_active = supports_toggle_shuffle_active
    self.supports_set_rating = supports_set_rating
    self.rating_system = rating_system

  def from_json(json_str):
    json_data = json.loads(json_str)
    supports_play_pause = json_data.get('supports_play_pause', False)
    supports_skip_previous = json_data.get('supports_skip_previous', False)
    supports_skip_next = json_data.get('supports_skip_next', False)
    supports_set_position = json_data.get('supports_set_position', False)
    supports_set_volume = json_data.get('supports_set_volume', False)
    supports_toggle_repeat_mode = json_data.get('supports_toggle_repeat_mode', False)
    supports_toggle_shuffle_active = json_data.get('supports_toggle_shuffle_active', False)
    supports_set_rating = json_data.get('supports_set_rating', False)
    rating_system = json_data.get('rating_system', "None")
    return MediaControls(supports_play_pause, supports_skip_next, supports_skip_previous, supports_set_position, supports_set_volume, supports_toggle_repeat_mode, supports_toggle_shuffle_active, supports_set_rating, rating_system)

  def try_play(self):
    WNPRedux._send_message('TRY_SET_STATE PLAYING')
    if WNPRedux.media_info._id == 'WINDOWS':
      WNPWindows.current_session.try_play_async()

  def try_pause(self):
    WNPRedux._send_message('TRY_SET_STATE PAUSED')
    if WNPRedux.media_info._id == 'WINDOWS':
      WNPWindows.current_session.try_pause_async()

  def try_toggle_play_pause(self):
    if WNPRedux.media_info.state == 'PLAYING':
      self.try_pause()
    else:
      self.try_play()
    if WNPRedux.media_info._id == 'WINDOWS':
      WNPWindows.current_session.try_toggle_play_pause_async()

  def try_skip_previous(self):
    WNPRedux._send_message('TRY_SKIP_PREVIOUS')
    if WNPRedux.media_info._id == 'WINDOWS':
      WNPWindows.current_session.try_skip_previous_async()

  def try_skip_next(self):
    WNPRedux._send_message('TRY_SKIP_NEXT')
    if WNPRedux.media_info._id == 'WINDOWS':
      WNPWindows.current_session.try_skip_next_async()

  def try_set_position_seconds(self, seconds):
    positionInSeconds = seconds
    if positionInSeconds < 0:
      positionInSeconds = 0
    if positionInSeconds > WNPRedux.media_info.duration_seconds:
      positionInSeconds = WNPRedux.media_info.duration_seconds
    # DurationSeconds or 1 is to prevent division by zero if the duration is unknown
    positionInPercent = positionInSeconds / (WNPRedux.media_info.duration_seconds or 1)
    # This makes sure it always gives us 0.0, not 0,0 (dot instead of comma, regardless of localization)
    positionInPercentString = str(positionInPercent)

    WNPRedux._send_message(f'TRY_SET_POSITION {positionInSeconds}:{positionInPercentString}')
    if WNPRedux.media_info._id == 'WINDOWS':
      WNPWindows.current_session.try_change_playback_position_async(positionInSeconds * 10_000_000)

  def try_revert_position_seconds(self, seconds):
    self.try_set_position_seconds(WNPRedux.media_info.position_seconds - seconds)

  def try_forward_position_seconds(self, seconds):
    self.try_set_position_seconds(WNPRedux.media_info.position_seconds + seconds)

  def try_set_position_percent(self, percent):
    seconds = round((percent / 100) * WNPRedux.media_info.duration_seconds)
    self.try_set_position_seconds(seconds)

  def try_revert_position_percent(self, percent):
    seconds = round((percent / 100) * WNPRedux.media_info.duration_seconds)
    self.try_set_position_seconds(WNPRedux.media_info.position_seconds - seconds)

  def try_forward_position_percent(self, percent):
    seconds = round((percent / 100) * WNPRedux.media_info.duration_seconds)
    self.try_set_position_seconds(WNPRedux.media_info.position_seconds + seconds)
  
  def try_set_volume(self, volume):
    new_volume = volume
    if volume < 0: new_volume = 0
    if volume > 100: new_volume = 100
    WNPRedux._send_message(f'TRY_SET_VOLUME {new_volume}')

  def try_toggle_repeat_mode(self):
    WNPRedux._send_message('TRY_TOGGLE_REPEAT_MODE')
    if (WNPRedux.media_info._id == 'WINDOWS'):
      WNPWindows.current_session.try_change_auto_repeat_mode_async()

  def try_toggle_shuffle_active(self):
    WNPRedux._send_message('TRY_TOGGLE_SHUFFLE_ACTIVE')
    if (WNPRedux.media_info._id == 'WINDOWS'):
      WNPWindows.current_session.try_change_shuffle_active_async()

  def try_set_rating(self, rating):
    WNPRedux._send_message(f'TRY_SET_RATING {rating}')

class MediaInfo:
  def __init__(self, timestamp_offset = 0):
    self.timestamp_offset = timestamp_offset
    self.controls = MediaControls()
    self._title = ''
    self._state = 'STOPPED'
    self._id = ''
    self.player_name = ''
    self.artist = ''
    self.album = ''
    self.cover_url = ''
    self.duration = '0:00'
    self.duration_seconds = 0
    self.position = '0:00'
    self.position_seconds = 0
    self.position_percent = 0
    self.volume = 100
    self.rating = 0
    self.repeat_mode = 'NONE'
    self.shuffle_active = False
    self.timestamp = 0
  
  @property
  def state(self):
    return self._state
  
  @state.setter
  def state(self, value):
    self._state = value
    self.timestamp = datetime.now().timestamp() + self.timestamp_offset
  
  @property
  def title(self):
    return self._title
  
  @title.setter
  def title(self, value):
    self._title = value
    if len(value) > 0: self.timestamp = datetime.now().timestamp() + self.timestamp_offset
    else: self.timestamp = 0
  
  @property
  def volume(self):
    return self._volume
  
  @volume.setter
  def volume(self, value):
    self._volume = value
    if self.state == 'PLAYING': self.timestamp = datetime.now().timestamp() + self.timestamp_offset

class WNPRedux:
  is_started = False
  is_using_native_apis = False
  listen_address = None
  wsPort = None
  media_info = MediaInfo()
  _media_info_dictionary: list[MediaInfo] = list()
  _server = None
  _loop = None
  _recipients = set()
  _clients = set()
  clients = 0
  _version = '0.0.0'
  _logger = None

  def start(wsPort, webPort, version, logger, listen_address = '127.0.0.1'):
    if WNPRedux.is_started: return
    WNPRedux.is_started = True
    WNPRedux.listen_address = listen_address
    WNPRedux.wsPort = wsPort
    WNPRedux.webPort = webPort
    WNPRedux.media_info = MediaInfo()
    WNPRedux._media_info_dictionary = list()
    WNPRedux._recipients = set()
    WNPRedux._clients = set()
    WNPRedux.clients = 0
    WNPRedux._version = version
    WNPRedux._logger = logger
    WNPRedux.is_using_native_apis = os.path.isdir(os.path.expanduser('~\\wnp_enable_native_api'))
    if WNPRedux.is_using_native_apis and is_windows: WNPWindows.start()
    Thread(target = WNPRedux._threaded_start).start()

  def _threaded_start():
    WNPRedux._loop = asyncio.new_event_loop()
    WNPRedux._server = WNPRedux._loop.run_until_complete(websockets.serve(
      WNPRedux._on_connect, WNPRedux.listen_address, WNPRedux.wsPort, loop=WNPRedux._loop
    ))
    WNPRedux._loop.run_until_complete(WNPRedux._server.wait_closed())

  def _send_message(message):
    for client in WNPRedux._clients:
      if client.id == WNPRedux.media_info._id:
        pool.submit(asyncio.run, client.send(message))
        break

  def log(type, message):
    if WNPRedux._logger == None: return
    WNPRedux._logger(type, message)

  def stop():
    if not WNPRedux.is_started: return
    try:
      WNPRedux.is_started = False
      WNPRedux.media_info = MediaInfo()
      WNPRedux._recipients.clear()
      WNPRedux._media_info_dictionary = list()
      WNPRedux._clients.clear()
      WNPRedux.clients = 0

      async def close():
        WNPRedux._server.close()
        await WNPRedux._server.wait_closed()

      closed = asyncio.run_coroutine_threadsafe(close(), WNPRedux._loop)
      closed.result(timeout=1.0)
      WNPRedux._loop.stop()
      if (is_windows): WNPWindows.stop()
    except: pass

  async def _on_connect(websocket):
    WNPRedux._clients.add(websocket)
    WNPRedux.clients = len(WNPRedux._clients)
    websocket.id = str(datetime.now())
    await websocket.send(f'ADAPTER_VERSION {WNPRedux._version};WNPRLIB_REVISION 2')
    try:
      async for message in websocket:
        try:
          if message.upper() == 'RECIPIENT':
            WNPRedux._recipients.add(websocket.id)
            WNPRedux._update_recipients()
            continue
          
          message_type = message[:message.index(' ')].upper()
          info = message[message.index(' ') + 1:]

          if (message_type == 'USE_NATIVE_APIS'):
            if (info.upper() == 'TRUE' and not WNPRedux.is_using_native_apis):
              os.rmdir(os.path.expanduser('~\\wnp_enable_native_api'))
              WNPRedux.is_using_native_apis = True
              if (is_windows): WNPWindows.start()
            elif info.upper() == 'FALSE' and WNPRedux.is_using_native_apis:
              os.mkdir(os.path.expanduser('~\\wnp_enable_native_api'))
              WNPRedux.is_using_native_apis = False;
              if (is_windows): WNPWindows.stop()
            continue

          current_media_info = MediaInfo()
          found = False
          for media_info in WNPRedux._media_info_dictionary:
            if media_info._id == websocket.id:
              current_media_info = media_info
              found = True
              break
            
          current_media_info._id = websocket.id

          if not found:
            WNPRedux._media_info_dictionary.append(current_media_info)

          if message_type == 'PLAYER_NAME':
            current_media_info.player_name = info
          elif message_type == 'PLAYER_CONTROLS':
            current_media_info.controls = MediaControls.from_json(info)
          elif message_type == 'STATE':
            current_media_info.state = info
          elif message_type == 'TITLE':
            current_media_info.title = info
          elif message_type == 'ARTIST':
            current_media_info.artist = info
          elif message_type == 'ALBUM':
            current_media_info.album = info
          elif message_type == 'COVER_URL':
            current_media_info.cover_url = info
          elif message_type == 'DURATION_SECONDS':
            current_media_info.duration_seconds = int(info)
            current_media_info.duration = time_in_seconds_to_string(current_media_info.duration_seconds)
            # I guess set PositionPercent to 0, because if duration changes, a new video is playing
            current_media_info.position_percent = 0
          elif message_type == 'POSITION_SECONDS':
            current_media_info.position_seconds = int(info)
            current_media_info.position = time_in_seconds_to_string(current_media_info.position_seconds)

            if (current_media_info.duration_seconds > 0):
              current_media_info.position_percent = (current_media_info.position_seconds / current_media_info.duration_seconds) * 100
            else:
              current_media_info.position_percent = 100
          elif message_type == 'VOLUME':
            current_media_info.volume = int(info)
          elif message_type == 'RATING':
            current_media_info.rating = int(info)
          elif message_type == 'REPEAT_MODE':
            current_media_info.repeat_mode = info
          elif message_type == 'SHUFFLE_ACTIVE':
            current_media_info.shuffle_active = info.upper() == 'TRUE'
          elif message_type == 'ERROR':
            WNPRedux.log('Error', f'WNPRedux - Browser Error: {info}')
          elif message_type == 'ERRORDEBUG':
            WNPRedux.log('Debug', f'WNPRedux - Browser Error Trace: {info}')
          else:
            WNPRedux.log('Warning', f'Unknown message type: {message_type}; ({message})')
          
          if message_type != 'POSITION' and len(current_media_info.title) > 0:
            WNPRedux._update_media_info()
          
          WNPRedux._update_recipients()
        except Exception as e:
          WNPRedux.log('Error', f'WNPRedux - Error parsing data from WebNowPlaying-Redux')
          WNPRedux.log('Debug', f'WNPRedux - Error Trace: {e}')
    except Exception:
      pass
    finally:
      WNPRedux._clients.discard(websocket)
      WNPRedux.clients = len(WNPRedux._clients)
      WNPRedux._recipients.discard(websocket.id)
      for media_info in WNPRedux._media_info_dictionary:
        if media_info._id == websocket.id:
          WNPRedux._media_info_dictionary.remove(media_info)
          break
      WNPRedux._update_media_info()
      WNPRedux._update_recipients()
  
  def _update_media_info():
    WNPRedux._media_info_dictionary = sorted(WNPRedux._media_info_dictionary, key=lambda x: x.timestamp, reverse=True)
    suitable_match = False

    for media_info in WNPRedux._media_info_dictionary:
      if media_info.state == 'PLAYING' and media_info.volume > 0:
        WNPRedux.media_info = media_info
        suitable_match = True
        break
    
    if not suitable_match:
      if len(WNPRedux._media_info_dictionary) > 0:
        WNPRedux.media_info = WNPRedux._media_info_dictionary[0]
      else:
        WNPRedux.media_info = MediaInfo()

  def _update_recipients():
    value = json.dumps(WNPRedux.media_info, default=lambda x: x.__dict__).replace('_title', 'title').replace('_state', 'state').replace('_volume', 'volume')
    for client in WNPRedux._clients:
      if client.id in WNPRedux._recipients:
        future = pool.submit(asyncio.run, client.send(value))
        try:
          future.result()
        except Exception: pass