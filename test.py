from src.pywnp import WNPRedux
import time

def logger(type, message):
  print(f"{type}: {message}")

def reconnect_test():
  WNPRedux.start(1234, '1.0.0', logger)
  try:
    for i in range(99999):
      print(WNPRedux.media_info.position)
      # print(WNPRedux.media_info.controls.__dict__)
      try:
        time.sleep(1)
      except:
        raise Exception
  except:
    WNPRedux.stop()
    reconnect_test()

def test():
  WNPRedux.start(1234, '1.2.0', logger)
  try:
    for i in range(99999):
      print(WNPRedux.media_info.title, WNPRedux.media_info.position)
      time.sleep(1)
  except:
    WNPRedux.stop()

# reconnect_test()
test()