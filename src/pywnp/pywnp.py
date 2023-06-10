from typing import (Dict, List, Set, Callable, Any)
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Thread
from aiohttp import web
import aiohttp
import asyncio
import random
import json
import math
import time
import sys
import os

# Gotta love having to put everything into one file because
# i'm too inexperienced with python to properly use modules.
# Please bring me back to a normal language.
# For now, everything will just be in a single file
# separated by comments to create sections.

# === UTILS ===

is_windows = sys.platform == 'win32'

def pad(num: int, size: int) -> str: return str(num).rjust(size, '0')
def time_in_seconds_to_string(time_in_seconds: int) -> str:
  try:
    if time_in_seconds == None: return '0:00'
    time_in_minutes = math.floor(time_in_seconds / 60)
    if time_in_minutes < 60:
      return str(time_in_minutes) + ':' + str(pad(math.floor(time_in_seconds % 60), 2))

    return str(math.floor(time_in_minutes / 60)) + ':' + str(pad(math.floor(time_in_minutes % 60), 2)) + ':' + str(pad(math.floor(time_in_seconds % 60), 2))
  except:
    return '0:00'

def get_wnp_path() -> str:
  # Note: I was going to clean up the old unused folder here but that might conflict with older WNP adapters, so I won't.
  if is_windows: return os.path.expandvars(r'%LocalAppData%\\WebNowPlaying')
  else: return os.path.expanduser(r'~\\.config\\WebNowPlaying')

# === END UTILS ===

# === START MEDIA CONTROLS ===

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

  @staticmethod
  def from_json(json_str: str):
    json_data: Dict[str, Any] = json.loads(json_str)
    supports_play_pause = json_data.get('supports_play_pause', False)
    supports_skip_previous = json_data.get('supports_skip_previous', False)
    supports_skip_next = json_data.get('supports_skip_next', False)
    supports_set_position = json_data.get('supports_set_position', False)
    supports_set_volume = json_data.get('supports_set_volume', False)
    supports_toggle_repeat_mode = json_data.get('supports_toggle_repeat_mode', False)
    supports_toggle_shuffle_active = json_data.get('supports_toggle_shuffle_active', False)
    supports_set_rating = json_data.get('supports_set_rating', False)
    rating_system = json_data.get('rating_system', 'None')
    return MediaControls(supports_play_pause, supports_skip_next, supports_skip_previous, supports_set_position, supports_set_volume, supports_toggle_repeat_mode, supports_toggle_shuffle_active, supports_set_rating, rating_system)

  def try_play(self):
    HttpServer.send_message('TRY_SET_STATE PLAYING')

  def try_pause(self):
    HttpServer.send_message('TRY_SET_STATE PAUSED')

  def try_toggle_play_pause(self):
    if WNPRedux.media_info.state == 'PLAYING': self.try_pause()
    else: self.try_play()

  def try_skip_previous(self):
    HttpServer.send_message('TRY_SKIP_PREVIOUS')

  def try_skip_next(self):
    HttpServer.send_message('TRY_SKIP_NEXT')

  def try_set_position_seconds(self, seconds: int):
    positionInSeconds = seconds
    if positionInSeconds < 0:
      positionInSeconds = 0
    if positionInSeconds > WNPRedux.media_info.duration_seconds:
      positionInSeconds = WNPRedux.media_info.duration_seconds
    # DurationSeconds or 1 is to prevent division by zero if the duration is unknown
    positionInPercent = positionInSeconds / (WNPRedux.media_info.duration_seconds or 1)
    # This makes sure it always gives us 0.0, not 0,0 (dot instead of comma, regardless of localization)
    positionInPercentString = str(positionInPercent)

    HttpServer.send_message(f'TRY_SET_POSITION {positionInSeconds}:{positionInPercentString}')

  def try_revert_position_seconds(self, seconds: int):
    self.try_set_position_seconds(WNPRedux.media_info.position_seconds - seconds)

  def try_forward_position_seconds(self, seconds: int):
    self.try_set_position_seconds(WNPRedux.media_info.position_seconds + seconds)

  def try_set_position_percent(self, percent: int):
    seconds = round((percent / 100) * WNPRedux.media_info.duration_seconds)
    self.try_set_position_seconds(seconds)

  def try_revert_position_percent(self, percent: float):
    seconds = round((percent / 100) * WNPRedux.media_info.duration_seconds)
    self.try_set_position_seconds(WNPRedux.media_info.position_seconds - seconds)

  def try_forward_position_percent(self, percent: float):
    seconds = round((percent / 100) * WNPRedux.media_info.duration_seconds)
    self.try_set_position_seconds(WNPRedux.media_info.position_seconds + seconds)
  
  def try_set_volume(self, volume: int):
    new_volume = volume
    if volume < 0: new_volume = 0
    if volume > 100: new_volume = 100
    HttpServer.send_message(f'TRY_SET_VOLUME {new_volume}')

  def try_toggle_repeat_mode(self):
    HttpServer.send_message('TRY_TOGGLE_REPEAT_MODE')

  def try_toggle_shuffle_active(self):
    HttpServer.send_message('TRY_TOGGLE_SHUFFLE_ACTIVE')

  def try_set_rating(self, rating: int):
    HttpServer.send_message(f'TRY_SET_RATING {rating}')

# === END  MEDIA CONTROLS ===

# === START MEDIA INFO ===

class MediaInfo:
  def __init__(self):
    self.controls = MediaControls()
    self._title: str = ''
    self._state: str = 'STOPPED'
    self._volume: int = 100
    self._id: str = ''
    self.is_native: bool = False
    self.player_name: str = ''
    self.artist: str = ''
    self.album: str = ''
    self.cover_url: str = ''
    self.duration: str = '0:00'
    self.duration_seconds: int = 0
    self.position: str = '0:00'
    self.position_seconds: int = 0
    self.position_percent: int = 0
    self.rating: int = 0
    self.repeat_mode: str = 'NONE'
    self.shuffle_active: bool = False
    self.timestamp: int = 0
  
  @property
  def state(self):
    return self._state
  
  @state.setter
  def state(self, value: str):
    if (self.state == value): return
    self._state = value
    self.timestamp = datetime.now().timestamp()
  
  @property
  def title(self):
    return self._title
  
  @title.setter
  def title(self, value: str):
    if (self._title == value): return
    self._title = value
    if len(value) > 0: self.timestamp = datetime.now().timestamp()
    else: self.timestamp = 0
  
  @property
  def volume(self):
    return self._volume
  
  @volume.setter
  def volume(self, value: int):
    if (self.volume == value): return
    self._volume = value
    if self.state == 'PLAYING': self.timestamp = datetime.now().timestamp()

# === START HTTP SERVER ===
  
class HttpServer:
  is_started: bool = False
  port: int = 0
  recipients: Set[web.WebSocketResponse] = set()
  clients: Set[web.WebSocketResponse] = set()
  pool: ThreadPoolExecutor = ThreadPoolExecutor()

  @staticmethod
  def start(port: int) -> None:
    if HttpServer.is_started: return
    HttpServer.is_started = True
    HttpServer.port = port
    Thread(target=HttpServer._start_threaded).start()

  @staticmethod
  def stop() -> None:
    if not HttpServer.is_started: return
    HttpServer.is_started = False
    HttpServer.recipients.clear()
    WNPRedux.clients = 0
    time.sleep(0.5) # enough time for .run() to notice we stopped

  @staticmethod
  async def _run():
    while HttpServer.is_started:
      await asyncio.sleep(0.1)

  @staticmethod
  def _start_threaded() -> None:
    try:
      app = web.Application()
      app.router.add_get('/cover', HttpServer.handle_cover_route)
      app.router.add_get('/', HttpServer.web_websocket_handler)

      loop = asyncio.new_event_loop()
      runner = web.AppRunner(app)
      loop.run_until_complete(runner.setup())

      site = web.TCPSite(runner, '127.0.0.1', HttpServer.port)
      loop.run_until_complete(site.start())
      loop.run_until_complete(HttpServer._run())
      for client in set(HttpServer.clients):
        loop.run_until_complete(client.close(code=aiohttp.WSCloseCode.GOING_AWAY, message='Server shutdown'))
      loop.run_until_complete(runner.cleanup())
      loop.stop()
    except:
      if not HttpServer.is_started: return
      time.sleep(5)
      HttpServer._start_threaded()

  @staticmethod
  def handle_cover_route(request: web.Request) -> web.Response:
    if not 'name' in request.query: return web.Response(text='No name was provided', content_type='text/html', status=400)
    file_name = request.query['name']
    if not file_name.endswith('.jpg'): return web.Response(text='Invalid image name', content_type='text/html', status=400)
    file_path = f'{get_wnp_path()}\\{file_name}'
    if not os.path.exists(file_path): return web.Response(text='Image not found', content_type='text/html', status=404)
    with open(file_path, 'rb') as f:
      image_data = f.read()
    return web.Response(body=image_data, content_type='image/jpeg', status=200)
  
  async def web_websocket_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    HttpServer.clients.add(ws)
    WNPRedux.clients = len(HttpServer.clients)
    ws.id = str(datetime.now())
    await ws.send_str(f'ADAPTER_VERSION {WNPRedux._version};WNPRLIB_REVISION 2')

    try:
      async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
          try:
            message = msg.data
            if message.upper() == 'RECIPIENT':
              HttpServer.recipients.add(ws.id)
              HttpServer.update_recipients()
              continue
            
            try:
              type: str = message[:message.index(' ')].upper()
              data: str = message[message.index(' ') + 1:]
            except ValueError:
              # The message doesn't have a space
              type: str = message.upper()
              data: str = ''

            if (type == 'USE_NATIVE_APIS'):
              WNPRedux.is_using_native_apis = bool(data)
              if WNPRedux.is_using_native_apis and os.path.isdir(WNPRedux._disable_native_apis_path):
                os.rmdir(WNPRedux._disable_native_apis_path)
              elif not WNPRedux.is_using_native_apis and not os.path.isdir(WNPRedux._disable_native_apis_path):
                os.makedirs(WNPRedux._disable_native_apis_path, exist_ok=True)
              WNPRedux.update_media_info()
              HttpServer.update_recipients()
              continue

            media_info = WNPRedux.get_media_info(ws.id)

            if type == 'PLAYER_NAME':
              media_info.player_name = data
            elif type == 'IS_NATIVE':
              media_info.is_native = bool(data)
            elif type == 'PLAYER_CONTROLS':
              media_info.controls = MediaControls.from_json(data)
            elif type == 'STATE':
              media_info.state = data
            elif type == 'TITLE':
              media_info.title = data
            elif type == 'ARTIST':
              media_info.artist = data
            elif type == 'ALBUM':
              media_info.album = data
            elif type == 'COVER_URL':
              media_info.cover_url = data
            elif type == 'DURATION_SECONDS':
              media_info.duration_seconds = int(data)
              media_info.duration = time_in_seconds_to_string(media_info.duration_seconds)
              # I guess set PositionPercent to 0, because if duration changes, a new video is playing
              media_info.position_percent = 0
            elif type == 'POSITION_SECONDS':
              media_info.position_seconds = int(data)
              media_info.position = time_in_seconds_to_string(media_info.position_seconds)

              if (media_info.duration_seconds > 0):
                media_info.position_percent = (media_info.position_seconds / media_info.duration_seconds) * 100
              else:
                media_info.position_percent = 100
            elif type == 'VOLUME':
              media_info.volume = int(data)
            elif type == 'RATING':
              media_info.rating = int(data)
            elif type == 'REPEAT_MODE':
              media_info.repeat_mode = data
            elif type == 'SHUFFLE_ACTIVE':
              media_info.shuffle_active = data.upper() == 'TRUE'
            elif type == 'ERROR':
              WNPRedux.log('Error', f'WNPRedux - Browser Error: {data}')
            elif type == 'ERRORDEBUG':
              WNPRedux.log('Debug', f'WNPRedux - Browser Error Trace: {data}')
            else:
              WNPRedux.log('Warning', f'Unknown message type: {type}; ({message})')
            
            if type != 'POSITION' and len(media_info.title) > 0:
              WNPRedux.update_media_info()
            
            HttpServer.update_recipients()
          except Exception as e:
            WNPRedux.log('Error', f'WNPRedux - Error parsing WebSocket data')
            WNPRedux.log('Debug', f'WNPRedux - Error Trace: {e}')
        elif msg.type == aiohttp.WSMsgType.ERROR:
          WNPRedux.log('Error', f'WNPRedux - Unknown Error in WebSocket connection')
          WNPRedux.log('Debug', f'WNPRedux - Error Trace: {ws.exception()}')
    finally:
      HttpServer.clients.discard(ws)
      WNPRedux.clients = len(HttpServer.clients)
      HttpServer.recipients.discard(ws.id)
      for media_info in WNPRedux.media_info_dictionary:
        if media_info._id == ws.id:
          WNPRedux.media_info_dictionary.remove(media_info)
          break
      WNPRedux.update_media_info()
      HttpServer.update_recipients()

    return ws

  @staticmethod
  def on_message_hook(message: str) -> None:
    pass

  @staticmethod
  def send_message(message: str) -> None:
    HttpServer.on_message_hook(message)
    for client in HttpServer.clients:
      if client.id == WNPRedux.media_info._id:
        HttpServer.pool.submit(asyncio.run, client.send_str(message))
        break

  @staticmethod
  def update_recipients() -> None:
    value = json.dumps(WNPRedux.media_info, default=lambda x: x.__dict__).replace('_title', 'title').replace('_state', 'state').replace('_volume', 'volume')
    for client in HttpServer.clients:
      if client.id in HttpServer.recipients:
        future = HttpServer.pool.submit(asyncio.run, client.send_str(value))
        try:
          future.result()
        except Exception: pass

# === END HTTPSERVER ===

# === START WNP REDUX ===

class WNPRedux:
  is_started: bool = False
  is_using_native_apis: bool = True
  _disable_native_apis_path = os.path.join(get_wnp_path(), 'use_native_apis');
  media_info: MediaInfo = MediaInfo()
  media_info_dictionary: List[MediaInfo] = list()
  clients: int = 0
  _version: str = '0.0.0'
  _logger: Callable = None

  @staticmethod
  def start(port: int, version: str, logger: Callable) -> None:
    if WNPRedux.is_started: return
    WNPRedux.is_started = True
    HttpServer.start(port)
    if is_windows: WNPReduxNative.start(port)
    WNPRedux.is_using_native_apis = not os.path.isdir(WNPRedux._disable_native_apis_path)
    WNPRedux._version = version
    WNPRedux._logger = logger
  
  @staticmethod
  def stop() -> None:
    if not WNPRedux.is_started: return
    WNPRedux.is_started = False
    HttpServer.stop()
    if is_windows: WNPReduxNative.stop()
    WNPRedux.media_info = MediaInfo()
    WNPRedux.media_info_dictionary.clear()

  @staticmethod
  def log(type: str, message: str) -> None:
    if WNPRedux._logger == None: return
    WNPRedux._logger(type, message)

  @staticmethod
  def update_media_info() -> None:
    filtered_dictionary = filter(lambda kv: not kv.is_native or WNPRedux.is_using_native_apis, WNPRedux.media_info_dictionary)
    WNPRedux.media_info_dictionary = sorted(filtered_dictionary, key=lambda x: x.timestamp, reverse=True)
    suitable_match = False

    for media_info in WNPRedux.media_info_dictionary:
      if media_info.state == 'PLAYING' and media_info.volume > 0:
        WNPRedux.media_info = media_info
        suitable_match = True
        break
    
    if not suitable_match:
      if len(WNPRedux.media_info_dictionary) > 0:
        WNPRedux.media_info = WNPRedux.media_info_dictionary[0]
      else:
        WNPRedux.media_info = MediaInfo()

  @staticmethod
  def get_media_info(id: str) -> MediaInfo:
    current_media_info = MediaInfo()
    found = False
    for media_info in WNPRedux.media_info_dictionary:
      if media_info._id == id:
        current_media_info = media_info
        found = True
        break

    if not found:
      WNPRedux.media_info_dictionary.append(current_media_info)
      
    current_media_info._id = id
    return current_media_info

# === END WNP REDUX ===

# === START WNP REDUX NATIVE ===

if is_windows:
  from winsdk.windows.media.control import\
    GlobalSystemMediaTransportControlsSession as Session,\
    GlobalSystemMediaTransportControlsSessionManager as SessionManager,\
    GlobalSystemMediaTransportControlsSessionMediaProperties as MediaProperties
  from winsdk.windows.storage.streams import \
    DataReader, Buffer, InputStreamOptions, IRandomAccessStreamReference
  from winsdk.windows.foundation import EventRegistrationToken

  class WinSession:
    def __init__(self, session: Session, media_properties_changed_token: EventRegistrationToken, playback_info_changed_token: EventRegistrationToken, timeline_properties_changed_token: EventRegistrationToken):
      self.session = session
      self.media_properties_changed_token = media_properties_changed_token
      self.playback_info_changed_token = playback_info_changed_token
      self.timeline_properties_changed_token = timeline_properties_changed_token

  class WNPReduxNative:
    is_started: bool = False
    port: int = 0
    manager: SessionManager | None = None
    last_position_seconds: int = 0
    is_optimistic_position_thread_started: bool = False
    id_prefix = 'WNPReduxNativeWindows_'
    win_sessions: Dict[str, WinSession] = dict()
    pool: ThreadPoolExecutor = ThreadPoolExecutor()

    @staticmethod
    def start(port: int) -> None:
      if WNPReduxNative.is_started: return
      WNPReduxNative.is_started = True
      WNPReduxNative.port = port
      HttpServer.on_message_hook = WNPReduxNative.on_message_hook
      Thread(target=WNPReduxNative.start_windows_api).start()
      Thread(target=WNPReduxNative.optimistic_position_threaded).start()

    @staticmethod
    def stop() -> None:
      if not WNPReduxNative.is_started: return
      WNPReduxNative.is_started = False
      WNPReduxNative.is_optimistic_position_thread_started = False
      HttpServer.on_message_hook = lambda: None
      # OBS fucking dies if we don't do this in a thread, but somehow it's fine calling it normally on session change
      Thread(target=WNPReduxNative.unregister_sessions).start()

    @staticmethod
    def unregister_sessions() -> None:
      try:
        for win_session in WNPReduxNative.win_sessions.values():
          win_session.session.remove_media_properties_changed(win_session.media_properties_changed_token)
          win_session.session.remove_playback_info_changed(win_session.playback_info_changed_token)
          win_session.session.remove_timeline_properties_changed(win_session.timeline_properties_changed_token)
        WNPReduxNative.win_sessions.clear()
      except: pass

    @staticmethod
    def optimistic_position_threaded() -> None:
      if WNPReduxNative.is_optimistic_position_thread_started: return
      WNPReduxNative.is_optimistic_position_thread_started = True
      while WNPReduxNative.is_started:
        if WNPRedux.media_info._id.startswith(WNPReduxNative.id_prefix) and WNPRedux.media_info.state == 'PLAYING':
          WNPReduxNative.last_position_seconds += 1
          WNPRedux.media_info.position_seconds = WNPReduxNative.last_position_seconds
          WNPRedux.media_info.position = time_in_seconds_to_string(WNPRedux.media_info.position_seconds)

          if WNPRedux.media_info.duration_seconds > 0:
            WNPRedux.media_info.position_percent = (WNPRedux.media_info.position_seconds / WNPRedux.media_info.duration_seconds) * 100
          else:
            WNPRedux.media_info.position_percent = 100
          HttpServer.update_recipients()
        time.sleep(1)

    @staticmethod
    def get_media_info(app_id: str) -> MediaInfo:
      id = WNPReduxNative.id_prefix + app_id

      media_info = WNPRedux.get_media_info(id)
      media_info.player_name = 'Windows Media Session'
      media_info.is_native = True

      return media_info

    @staticmethod
    def on_message_hook(message: str) -> None:
      if not WNPRedux.media_info._id.startswith(WNPReduxNative.id_prefix): return
      try:
        media_info = WNPReduxNative.get_media_info(WNPRedux.media_info._id.replace(WNPReduxNative.id_prefix))
        if not media_info._id.replace(WNPReduxNative.id_prefix, '') in WNPReduxNative.win_sessions: return
        winSession: WinSession = WNPReduxNative.win_sessions[media_info._id.replace(WNPReduxNative.id_prefix, '')]

        try:
          type: str = message[:message.index(' ')].upper()
          data: str = message[message.index(' ') + 1:]
        except ValueError:
          # The message doesn't have a space
          type: str = message.upper()
          data: str = ''

        if type == 'TRY_SET_STATE': 
          if data == 'PLAYING': winSession.session.try_play_async()
          else: winSession.session.try_pause_async()
        elif type == 'TRY_SKIP_PREVIOUS': winSession.session.try_skip_previous_async()
        elif type == 'TRY_SKIP_NEXT': winSession.session.try_skip_next_async()
        elif type == 'TRY_SET_POSITION': winSession.session.try_change_playback_position_async(int(data.split(':')[0]) * 10_000_000)
        elif type == 'TRY_SET_VOLUME': pass
        elif type == 'TRY_TOGGLE_REPEAT_MODE': winSession.session.try_change_auto_repeat_mode_async()
        elif type == 'TRY_TOGGLE_SHUFFLE_ACTIVE': winSession.session.try_change_shuffle_active_async()
        elif type == 'TRY_SET_RATING': pass
      except Exception as ex:
        WNPRedux.log('Error', 'WNPNativeWindows - Failed to execute event')
        WNPRedux.log('Debug', f'WNPNativeWindows - Error Trace: {ex}')
  
    @staticmethod
    def start_windows_api() -> None:
      WNPReduxNative.manager: SessionManager = WNPReduxNative.pool.submit(asyncio.run, WNPReduxNative.request_session_manager()).result()
      WNPReduxNative.sessions_changed_native(WNPReduxNative.manager, None)
      WNPReduxNative.manager.add_sessions_changed(WNPReduxNative.sessions_changed_native)

    @staticmethod
    async def request_session_manager() -> SessionManager:
      return await SessionManager.request_async()

    @staticmethod
    def sessions_changed_native(manager: SessionManager, e) -> None:
      WNPReduxNative.unregister_sessions()

      sessions = manager.get_sessions()
      if sessions == None: return
      new_sessions: List[str] = list()
      for session in sessions:
        if WNPReduxNative.is_app_blacklisted(session.source_app_user_model_id): continue
        WNPReduxNative.media_properties_changed_native(session, None)
        WNPReduxNative.playback_info_changed_native(session, None)
        WNPReduxNative.timeline_properties_changed_native(session, None)
        media_properties_changed_token = session.add_media_properties_changed(WNPReduxNative.media_properties_changed_native)
        playback_info_changed_token = session.add_playback_info_changed(WNPReduxNative.playback_info_changed_native)
        timeline_properties_changed_token = session.add_timeline_properties_changed(WNPReduxNative.timeline_properties_changed_native)
        WNPReduxNative.win_sessions[session.source_app_user_model_id] = WinSession(session, media_properties_changed_token, playback_info_changed_token, timeline_properties_changed_token)
        new_sessions.append(session.source_app_user_model_id)
      
      keys_to_remove: List[str] = list()
      for media_info in WNPRedux.media_info_dictionary:
        if media_info._id.startswith(WNPReduxNative.id_prefix):
          if not media_info._id.replace(WNPReduxNative.id_prefix, '') in new_sessions:
            keys_to_remove.append(media_info._id)
      for key in keys_to_remove:
        for media_info in WNPRedux.media_info_dictionary:
          if media_info._id == key:
            WNPRedux.media_info_dictionary.remove(media_info)
            break
      WNPRedux.update_media_info()

    @staticmethod
    def is_app_blacklisted(app_id: str) -> bool:
      id = app_id.lower()
      if 'chrome' in id: return True
      if 'chromium' in id: return True
      if 'msedge' in id: return True
      if 'opera' in id: return True
      if 'brave' in id: return True
      if 'vivaldi' in id: return True
      if '308046B0AF4A39CB'.lower() in id: return True # firefox
      if '6F193CCC56814779'.lower() in id: return True # firefox nightly
      if '6F940AC27A98DD61'.lower() in id: return True # waterfox
      if 'A3665BA0C7D475A'.lower() in id: return True # pale moon
      return False
    
    @staticmethod
    def media_properties_changed_native(session: Session, e) -> None:
      info = WNPReduxNative.pool.submit(asyncio.run, WNPReduxNative.media_properties_changed_coroutine(session)).result()
      if (info == None): return
      media_info = WNPReduxNative.get_media_info(session.source_app_user_model_id)
      cover_url = WNPReduxNative.pool.submit(asyncio.run, WNPReduxNative.write_thumbnail(info.thumbnail)).result()
      media_info.cover_url = cover_url
      media_info.title = info.title or ''
      media_info.artist = info.artist or ''
      WNPRedux.update_media_info()
      HttpServer.update_recipients()

    @staticmethod
    async def media_properties_changed_coroutine(session: Session) -> MediaProperties | None:
      # Sometimes, we get 'The device != ready'. This can easily be replicated by opening foobar2000 while this is running.
      try:
        return await session.try_get_media_properties_async()
      except: pass

    @staticmethod
    async def write_thumbnail(thumbnail: IRandomAccessStreamReference | None) -> str:
      if thumbnail == None: return ''
      try:
        readable_stream = await thumbnail.open_read_async()
        buffer = Buffer(readable_stream.size)
        await readable_stream.read_async(buffer, buffer.capacity, InputStreamOptions.READ_AHEAD)
        if buffer.length == 0: return
        buffer_reader = DataReader.from_buffer(buffer)
        byte_buffer = buffer_reader.read_buffer(buffer.length)
        os.makedirs(get_wnp_path(), exist_ok=True)
        path = f'{get_wnp_path()}\\cover-{WNPReduxNative.port}.jpg'
        with open(path, 'wb+') as fobj:
          fobj.write(bytearray(byte_buffer))
        return f'http://127.0.0.1:{WNPReduxNative.port}/cover?name=cover-{WNPReduxNative.port}.jpg&r={random.randint(0, 999999)}'
      except: return ''

    @staticmethod
    def playback_info_changed_native(session: Session, e) -> None:
      info = session.get_playback_info()
      media_info = WNPReduxNative.get_media_info(session.source_app_user_model_id)

      controls_json = json.dumps({
        'supports_play_pause': info.controls.is_play_pause_toggle_enabled,
        'supports_skip_previous': info.controls.is_previous_enabled,
        'supports_skip_next': info.controls.is_next_enabled,
        'supports_set_position': info.controls.is_playback_position_enabled,
        'supports_set_volume': False,
        'supports_toggle_repeat_mode': info.controls.is_repeat_enabled,
        'supports_toggle_shuffle_active': info.controls.is_shuffle_enabled,
        'supports_set_rating': False,
        'rating_system': 'NONE'
      })

      repeat_mode = 'NONE'
      if info.auto_repeat_mode == None:
        repeat_mode = 'NONE'
      else:
        if info.auto_repeat_mode.value == 0:
          repeat_mode = 'NONE'
        elif info.auto_repeat_mode.value == 1:
          repeat_mode = 'ONE'
        elif info.auto_repeat_mode.value == 2:
          repeat_mode = 'ALL' 

      state = 'STOPPED'
      if info.playback_status == None:
        state = 'STOPPED'
      elif info.playback_status.value == 4:
        state = 'PLAYING'
      else:
        state = 'PAUSED'

      media_info.controls = MediaControls.from_json(controls_json)
      media_info.state = state
      media_info.repeat_mode = repeat_mode
      WNPRedux.update_media_info()
      HttpServer.update_recipients()

    @staticmethod
    def timeline_properties_changed_native(session: Session, e) -> None:
      info = session.get_timeline_properties()

      media_info = WNPReduxNative.get_media_info(session.source_app_user_model_id)

      media_info.duration_seconds = int(info.end_time.total_seconds())
      media_info.duration = time_in_seconds_to_string(media_info.duration_seconds)

      WNPReduxNative.last_position_seconds = int(info.position.total_seconds())
      media_info.position_seconds = WNPReduxNative.last_position_seconds
      media_info.position = time_in_seconds_to_string(media_info.position_seconds)

      if media_info.duration_seconds > 0:
        media_info.position_percent = (media_info.position_seconds / media_info.duration_seconds) * 100
      else:
        media_info.position_percent = 100

      WNPRedux.update_media_info()
      HttpServer.update_recipients()
    
# === END WNP REDUX NATIVE ===