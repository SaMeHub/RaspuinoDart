#!/usr/bin/env python
# from circuits import Component, Debugger, Event
from circuits import Component, Event
from circuits.net.events import write
# from circuits.web import Controller, Logger, Server
from circuits.web import Server
from circuits.web.dispatchers import WebSocketsDispatcher
from circuits.io import Serial
from circuits.tools import tryimport
from datetime import datetime

# #############################################################################
# some helper functions

def log(x, max = 120):
  x = str(x)
  print "{:%Y-%m-%d %H:%M:%S} - {}".format(datetime.now(), ((x[:max - 3] + "...") if len(x) > max else x))

# #############################################################################
# global event definitions

class receiveInput(Event):
    """ receiving input (from clients or the board) """

class broadcast(Event):
    """ broadcast data to all clients """

# #############################################################################
# game-master class

class RaspuinoDartMiniGame(Component):

  def __init__(self):
    log("RaspuinoDartMiniGame::__init__")
    Component.__init__(self)

  def receiveInput(self, data):
    log("RaspuinoDartMiniGame::receiveInput({})".format(data))
    self.fireEvent(broadcast(data))

# #############################################################################
# websockets class

class RaspuinoDartMiniEcho(Component):
  channel = "wsserver"

  def init(self):
    log("RaspuinoDartMiniEcho::init")
    self.clients = {}

  def connect(self, socket, host, port):
    log("RaspuinoDartMiniEcho::connect({}, {}, {})".format(id(socket), host, port))
    self.clients[socket] = {"host": host, "port": port}
    self.fireEvent(write(socket, "welcome %s:%d, you're connection number %d" % (host, port, len(self.clients))))
    self.broadcast("%s:%d joined as number %d" % (host, port, len(self.clients)))

  def disconnect(self, socket):
    log("RaspuinoDartMiniEcho::disconnect({}) <= {}, {}".format(id(socket), host, port))
    print "%s:%s disconnected" % (self.clients[socket]["host"], self.clients[socket]["port"])
    for sock in self.clients:
      self.fireEvent(write(sock, "%s:%d left, with %d connections remaining" % (self.clients[socket]["host"], self.clients[socket]["port"], len(self.clients) - 1)))
    if socket in self.clients:
      del self.clients[socket]

  def broadcast(self, data):
    log("RaspuinoDartMiniEcho::broadcast({})".format(data))
    for sock in self.clients:
      self.fireEvent(write(sock, data))

# #############################################################################
# server wrapper class

class RaspuinoDartMiniServer(Server):
  def __init__(self):
    log("RaspuinoDartMiniServer::__init__")
    Server.__init__(self, ("0.0.0.0", 8000))
    # Static(docroot=".", defaults=['RaspuinoDartMini.html']).register(self)
    RaspuinoDartMiniEcho().register(self)
    WebSocketsDispatcher("/websocket").register(self)

# #############################################################################
# serial board-connect class

# http://pydoc.net/Python/circuits/2.0.0/circuits.io.serial/
serial = tryimport("serial")
class RaspuinoDartMiniBoard(Component):
  channel = 'serial'

  def __init__(self, port = '/dev/ttyACM0', baudrate = 115200, bufsize = 1, timeout = 0, channel = channel):
    log("RaspuinoDartMiniBoard::__init__({})".format(port))
    super(RaspuinoDartMiniBoard, self).__init__(channel = channel)
    if serial is None:
      log("no USB connection")
    else:
      Serial(port, baudrate, bufsize, timeout).register(self)
    self.serial_matrix = {
       51:'D20',  67:'o20',  83:'T20',  99:'i20',
       50:'D01',  66:'o01',  82:'T01',  98:'i01',
       49:'D18',  65:'o18',  81:'T18',  33:'i18',
       48:'D04',  64:'o04',  96:'T04',  16:'i04',
       68:'D13',  80:'o13',  32:'T13',   0:'i13',
       84:'D06',  97:'o06',  17:'T06',   1:'i06',
      100:'D10',  34:'o10',  18:'T10',   2:'i10',
       36:'D15',  35:'o15',  19:'T15',   3:'i15',
       38:'D02',  39:'o02',   7:'T02',  23:'i02',
      102:'D17',  40:'o17',   8:'T17',  24:'i17',
       86:'D03',  41:'o03',   9:'T03',  25:'i03',
       70:'D19', 106:'o19',  10:'T19',  26:'i19',
       54:'D07',  91:'o07',  43:'T07',  27:'i07',
       59:'D16',  75:'o16', 107:'T16',  11:'i16',
       58:'D08',  74:'o08',  90:'T08',  42:'i08',
       57:'D11',  73:'o11',  89:'T11', 105:'i11',
       56:'D14',  72:'o14',  88:'T14', 104:'i14',
       55:'D09',  71:'o09',  87:'T09', 103:'i09',
       53:'D12',  69:'o12', 101:'T12',   5:'i12',
       52:'D05',  85:'o05',  37:'T05',  21:'i05',
        4:'DBE',   6:'BE'
    }

  def read(self, data):
    log("RaspuinoDartMiniBoard::read({})".format(self.serial_matrix[ord(data)]))
    self.fireEvent(receiveInput('dart' + self.serial_matrix[ord(data)]))
    # self.fireEvent(broadcast('dart' + self.serial_matrix[ord(data)]))
    self.flush()

# #############################################################################
# global wrapper class

class RaspuinoDartMini(Component):
  def __init__(self):
    log("RaspuinoDartMini::__init__")
    Component.__init__(self)
    RaspuinoDartMiniGame().register(self)
    RaspuinoDartMiniServer().register(self)
    RaspuinoDartMiniBoard().register(self)

# #############################################################################
# the main execute

if __name__ == "__main__":
  m = RaspuinoDartMini()
  m.run()
