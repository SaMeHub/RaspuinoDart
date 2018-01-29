#!/usr/bin/env python
from circuits import Component, Debugger, Event
from circuits.net.events import write
from circuits.web import Controller, Logger, Server, Static
from circuits.web.dispatchers import WebSocketsDispatcher
from circuits.io import Serial
from circuits.tools import tryimport
import json
import copy
import time
import sqlite3
from datetime import datetime
from random import randrange
from operator import itemgetter

# #############################################################################
# some helper functions

validDarts = [
  "D01", "D02", "D03", "D04", "D05", "D06", "D07", "D08", "D09", "D10", "D11", "D12", "D13", "D14", "D15", "D16", "D17", "D18", "D19", "D20",
  "o01", "o02", "o03", "o04", "o05", "o06", "o07", "o08", "o09", "o10", "o11", "o12", "o13", "o14", "o15", "o16", "o17", "o18", "o19", "o20",
  "T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08", "T09", "T10", "T11", "T12", "T13", "T14", "T15", "T16", "T17", "T18", "T19", "T20",
  "i01", "i02", "i03", "i04", "i05", "i06", "i07", "i08", "i09", "i10", "i11", "i12", "i13", "i14", "i15", "i16", "i17", "i18", "i19", "i20",
  "DBE", "BE", "XXX", "xxx"
]

def knuth_shuffle(x):
  for i in range(len(x)-1, 0, -1):
    j = randrange(i + 1)
    x[i], x[j] = x[j], x[i]

def log(x, max = 120):
  x = str(x)
  print "{:%Y-%m-%d %H:%M:%S} - {}".format(datetime.now(), ((x[:max - 3] + "...") if len(x) > max else x))

def getDartInfo(dart):
  # log("getDartInfo({})".format(dart))
  dartScore = 0
  multiplier = 1
  dartName = ""
  if dart.startswith("D"):
    multiplier = 2
    dartName += "double "
  elif dart.startswith("T"):
    multiplier = 3
    dartName += "triple "
  if "BE" in dart:
    dartScore = 25
    dartName += "bulls eye"
  elif dart == "XXX":
    dartName += "miss"
  elif dart == "xxx":
    dartName += "skipped"
  else:
    dartScore = int(dart[1:].lstrip("0"))
    dartName += dart[1:].lstrip("0")
  return {"score": dartScore * multiplier, "number": dartScore, "multiplier": multiplier, "name": dartName}

def len0(input):
  # log("len0({})".format(input))
  if input:
    return len(input)
  else:
    return 0

def nth(input):
  number = int(input)
  if number % 10 == 1:
    return "{}st".format(number)
  elif number % 10 == 2:
    return "{}nd".format(number)
  elif number % 10 == 3:
    return "{}rd".format(number)
  else:
    return "{}th".format(number)

# #############################################################################
# global event definitions

class receiveInput(Event):
    """ receiving input (from clients or the board) """

class broadcast(Event):
    """ broadcast data to all clients """

# #############################################################################
# the actualt match class

class RaspuinoDartMatch(Component):
  # apparently has to be a component instead of an object for the fireEvent(broadcast()) call to work!?
  def __init__(self, short = "", description = "", players = {}):
    log("RaspuinoDartMatch::__init__({}, {}, {})".format(type, description, players))
    Component.__init__(self)
    self.ongoing = True
    self.numberOfDarts = 3
    self.short = short
    self.description = description
    self.players = players
    self.history = [{"player": 0, "frame": 0}]
    self.nextup = {"player": 0, "frame": 0, "dart": 0}
    self.printRaspuinoDartMatch()
    self.applyRules()
    self.moveHistory()

  def printRaspuinoDartMatch(self):
    log("RaspuinoDartMatch::printRaspuinoDartMatch()")
    log(">> ongoing = {}".format(self.ongoing))
    log(">> numberOfDarts = {}".format(self.numberOfDarts))
    log(">> short = {}".format(self.short))
    log(">> description = {}".format(self.description))
    log(">> players = {}".format(self.players))
    log(">> history = {}".format(self.history))
    log(">> nextup = {}".format(self.nextup))

  def historyToNextup(self):
    p = self.history[0]["player"]
    f = self.history[0]["frame"]
    if len(self.players[p]["frames"]) > f:
      d = len(self.players[p]["frames"][f])
    else:
      d = 0
    self.nextup = {"player": p, "frame": f, "dart": d}

  def moveHistory(self):
    log("RaspuinoDartMatch::moveHistory()")
    if self.ongoing:
      p = self.history[0]["player"]
      f = self.history[0]["frame"]
      if len(self.players[p]["frames"]) > f:
        d = len(self.players[p]["frames"][f])
      else:
        d = 0
      if d >= self.numberOfDarts or self.players[p]["done"]:
        lowestframe = 1e6
        for (i, player) in self.players.items():
          if not player["done"] and len(player["frames"]) < lowestframe:
            lowestframe = len(player["frames"])
        lowplayer = -1
        for (i, player) in self.players.items():
          if not player["done"] and len(player["frames"]) == lowestframe:
            lowplayer = i
            break
        self.history.insert(0, {"player": lowplayer, "frame": len(self.players[lowplayer]["frames"])})
      if (p == f == d == 0) or p != self.history[0]["player"]:
        self.fireEvent(broadcast("message" + json.dumps({"messagetitle": "Next player", "messagetext": self.players[self.history[0]["player"]]["name"] + ", it's your turn!", "show": 1000})))
      self.historyToNextup()
    else:
      pass

  def addDart(self, input):
    log("RaspuinoDartMatch::addDart({})".format(input))
    if self.ongoing and input in validDarts:
      if len(self.players[self.history[0]["player"]]["frames"]) <= self.history[0]["frame"]:
        self.players[self.history[0]["player"]]["frames"].append([])
      self.players[self.history[0]["player"]]["frames"][self.history[0]["frame"]].append(input)
      self.fireEvent(broadcast("message" + json.dumps({"messagetitle": self.players[self.history[0]["player"]]["name"], "messagetext": getDartInfo(input)["name"]})))
      self.fireEvent(broadcast("darts" + input))
      self.applyRules()
      self.moveHistory()
      self.clientData()
    else:
      log("match already finished!!")

  def clearFrame(self):
    log("RaspuinoDartMatch::clearFrame()")

  def undoDart(self):
    log("RaspuinoDartMatch::undoDart()")
    p = self.history[0]["player"]
    f = self.history[0]["frame"]
    if len(self.players[p]["frames"]) > f:
      d = len(self.players[p]["frames"][f])
    else:
      d = 0
    if len(self.history) + d > 1:
      if d == 0:
        if self.history[0]["frame"] < len(self.players[self.history[0]["player"]]["frames"]):
          self.players[self.history[0]["player"]]["frames"].pop()
        self.history.pop(0)
        self.players[self.history[0]["player"]]["frames"][self.history[0]["frame"]].pop()
        # self.players[self.history[0]["player"]]["done"] = False
      else:
        self.players[p]["frames"][f].pop()
        # self.players[p]["done"] = False
      # self.ongoing = True
      self.applyRules()
      self.moveHistory()
      self.clientData()

  def skipFrame(self, hist):
    log("RaspuinoDartMatch::skipFrame({})".format(hist))
    if len(self.players[hist["player"]]["frames"]) > 0 and hist["frame"] < len(self.players[hist["player"]]["frames"]):
      self.players[hist["player"]]["frames"][hist["frame"]] = ["xxx", "xxx", "xxx"]

  def checkAllDone(self):
    log("RaspuinoDartMatch::checkAllDone()")
    self.ongoing = True
    countdone = 0
    highrank = 0
    ranks = {}
    for (p, player) in self.players.items():
      if player["done"]:
        countdone += 1
        ranks[player["rank"]] = p
        if player["rank"] > highrank:
          highrank = player["rank"]
    if len(self.players) - countdone < 2:
      for (p, player) in self.players.items():
        if player["rank"] == 0:
          player["done"] = True
          player["rank"] = highrank + 1
          player["info"] = [nth(player["rank"])]
          ranks[player["rank"]] = p
      self.ongoing = False
      messagesilent = ""
      for (r, p) in ranks.items():
        messagesilent += nth(r) + " " + self.players[p]["name"] + "<br />"
      message = {"messagetitle": "Game over", "messagetext": "{} wins!".format(self.players[ranks[1]]["name"]), "messagesilent": messagesilent, "show": 1000, "hide": 10000}
      self.fireEvent(broadcast("message" + json.dumps(message)))
      log("the match is over")
      return True
    return False

  def applyRules(self):
    log("RaspuinoDartMatch::applyRules()")
    rank = 1

    if self.short in ["301", "301D", "301T", "501", "501D", "501T"]: # list ids for N01 games
      for (p, player) in self.players.items():
        startvalue = int(self.short[:3])
        player["score"] = startvalue
        player["info"] = []
        player["done"] = False
        player["rank"] = 0
      for h, hist in reversed(list(enumerate(self.history))):
        if len(self.players[hist["player"]]["frames"]) > 0:
          for dart in self.players[hist["player"]]["frames"][hist["frame"]]:
            self.players[hist["player"]]["info"] = []
            self.players[hist["player"]]["score"] -= getDartInfo(dart)["score"]
            if self.short.endswith('T'):
              if dart.startswith("T") and self.players[hist["player"]]["score"] == 0:
                self.players[hist["player"]]["done"] = True
                self.players[hist["player"]]["rank"] = rank
                self.players[hist["player"]]["info"] = [nth(self.players[hist["player"]]["rank"])]
                rank += 1
                if self.checkAllDone():
                  return
              elif self.players[hist["player"]]["score"] < 3:
                self.skipFrame(hist)
                self.applyRules()
                return
            elif self.short.endswith('D'):
              if dart.startswith("D") and self.players[hist["player"]]["score"] == 0:
                self.players[hist["player"]]["done"] = True
                self.players[hist["player"]]["rank"] = rank
                self.players[hist["player"]]["info"] = [nth(self.players[hist["player"]]["rank"])]
                rank += 1
                if self.checkAllDone():
                  return
              elif self.players[hist["player"]]["score"] < 2:
                self.skipFrame(hist)
                self.applyRules()
                return
            else:
              if self.players[hist["player"]]["score"] == 0:
                self.players[hist["player"]]["done"] = True
                self.players[hist["player"]]["rank"] = rank
                self.players[hist["player"]]["info"] = [nth(self.players[hist["player"]]["rank"])]
                rank += 1
                if self.checkAllDone():
                  return
              elif self.players[hist["player"]]["score"] < 0:
                self.skipFrame(hist)
                self.applyRules()
                return
    elif self.short.startswith('CRK'):
      numberOfHits = 3
      numbersToHit = {15: 0, 16:0, 17:0, 18:0, 19:0, 20:0, 25:0}
      cricketdata = {}
      for (p, player) in self.players.items():
        player["score"] = 0
        player["info"] = []
        player["done"] = False
        player["rank"] = 0
      for h, hist in reversed(list(enumerate(self.history))):
        if not hist["frame"] in cricketdata.keys():
          cricketdata[hist["frame"]] = {}
          cricketdata[hist["frame"]][-1] = {"numbersToHit": copy.deepcopy(numbersToHit)}
          for (p, player) in self.players.items():
            if hist["frame"] == 0:
              cricketdata[0][p] = {"numbersToHit": copy.deepcopy(numbersToHit)}
            else:
              cricketdata[hist["frame"]][p] = {"numbersToHit": copy.deepcopy(cricketdata[hist["frame"] - 1][p]["numbersToHit"])}
        if len(self.players[hist["player"]]["frames"]) > 0:
          for dart in self.players[hist["player"]]["frames"][hist["frame"]]:
            dartScore = getDartInfo(dart)
            for i in xrange(dartScore["multiplier"]):
              if dartScore["number"] in cricketdata[hist["frame"]][hist["player"]]["numbersToHit"].keys():
                if cricketdata[hist["frame"]][hist["player"]]["numbersToHit"][dartScore["number"]] < numberOfHits:
                  cricketdata[hist["frame"]][hist["player"]]["numbersToHit"][dartScore["number"]] += 1
                else:
                  cricketdata[hist["frame"]][hist["player"]]["numbersToHit"][dartScore["number"]] += 1
                  cricketdata[hist["frame"]][-1]["numbersToHit"][dartScore["number"]] += 1
                  if self.short == "CRK":
                    isOpenPlayers = False
                    for (p, player) in cricketdata[hist["frame"]].items():
                      if p >= 0 and player["numbersToHit"][dartScore["number"]] < numberOfHits:
                        isOpenPlayers = True
                    if isOpenPlayers:
                      self.players[hist["player"]]["score"] += dartScore["number"]
                  elif self.short == "CTCRK":
                    for (p, player) in cricketdata[hist["frame"]].items():
                      if p >= 0 and player["numbersToHit"][dartScore["number"]] < numberOfHits:
                        self.players[p]["score"] += dartScore["number"]

      if self.short in ["CRKF", "CTCRKF"]: # 'fair' matches
        for (f, frame) in cricketdata.items():
          # check if all players have finished this frame
          countFinPlayers = 0
          for (p, player) in self.players.items():
            if len(player["frames"]) > f:
              if len(player["frames"][f]) == self.numberOfDarts:
                countFinPlayers += 1
          if countFinPlayers == len(self.players):
            for (number, count) in cricketdata[f][-1]["numbersToHit"].items():
              if count > 0:
                if self.short == "CRKF":
                  isOpenPlayers = False
                  for (p, player) in cricketdata[f].items():
                    if p >= 0 and player["numbersToHit"][number] < numberOfHits:
                      isOpenPlayers = True
                  if isOpenPlayers:
                    for (p, player) in cricketdata[f].items():
                      if p >= 0 and player["numbersToHit"][number] >= numberOfHits:
                        self.players[p]["score"] += number * (player["numbersToHit"][number] - numberOfHits)
                elif self.short == "CTCRKF":
                  for (p, player) in cricketdata[f].items():
                    if p >= 0 and player["numbersToHit"][number] < numberOfHits:
                      self.players[p]["score"] += number * count

      # might need some adaption to fair modes, cause ranks could be shared somehow!?
      # find cases and prevent them!?
      for (p, player) in self.players.items():
        lastFrame = len(player["frames"]) - 1 if len(player["frames"]) else 0
        countOpenNumbers = 0
        player["info"] = []
        for (o, count) in cricketdata[lastFrame][p]["numbersToHit"].items():
          info = "{0!s} ".format(o)
          for i in xrange(numberOfHits):
            if i < count:
              info += "#"
            else:
              info += "-"
              countOpenNumbers += 1
          player["info"].append(info)
        if countOpenNumbers == 0:
          refscore = True
          for (p2, player2) in self.players.items():
            if (self.short in [6] and not player2["done"] and player2["score"] > player["score"]) \
              or (self.short in [8] and not player2["done"] and player2["score"] < player["score"]):
              refscore = False
          if refscore:
            player["done"] = True
            player["rank"] = rank
            player["info"] = [nth(player["rank"])]
            rank += 1
            if self.checkAllDone():
              return
          else:
            player["done"] = False
            player["rank"] = 0
        else:
          player["done"] = False
          player["rank"] = 0
    else:
      pass

  def clientData(self):
    log("RaspuinoDartMatch::clientData()")
    currentmatch = {
      "short": self.short,
      "description": self.description,
      "players": self.players,
      "nextup": self.nextup
    }
    # self.printRaspuinoDartMatch()
    self.fireEvent(broadcast("currentmatch" + json.dumps(currentmatch)))

# #############################################################################
# game-master class

class RaspuinoDartGame(Component):

  def __init__(self):
    log("RaspuinoDartGame::__init__")
    Component.__init__(self)
    self.currentMatch = None
    self.playerData = {}
    self.matchData = {}
    self.matchTypes = {
      0: {"short": "301"  , "description": "301"},
      1: {"short": "301D" , "description": "301 double out"},
      2: {"short": "301T" , "description": "301 triple out"},
      3: {"short": "501"  , "description": "501"},
      4: {"short": "501D" , "description": "501 double out"},
      5: {"short": "501T" , "description": "501 triple out"},
      6: {"short": "CRK"  , "description": "Cricket"},
      7: {"short": "CRKF" , "description": "Cricket (fair)"},
      8: {"short": "CTCRK" , "description": "Cut-throat Cricket"},
      9: {"short": "CTCRKF", "description": "Cut-throat Cricket (fair)"},
    }

    # set some starting values for now
    self.playerData = {
      0: {"id": 0, "name": "Sascha", "joined": "20170210-000000", "matches": [0, 1]},
      1: {"id": 1, "name": "Heike" , "joined": "20170210-000000", "matches": []},
      2: {"id": 2, "name": "Michi" , "joined": "20170210-000000", "matches": [0, 1]},
      3: {"id": 3, "name": "Jochen", "joined": "20170210-000000", "matches": [0, 1]},
    }
    self.matchData = {
      0: {"type": 0, "datetime": datetime.now().strftime("%Y%m%d-%H%M%S"), "players": [0, 2, 3], "history": []},
      1: {"type": 0, "datetime": datetime.now().strftime("%Y%m%d-%H%M%S"), "players": [3, 0, 2], "history": []}
    }
    # self.printPlayerData()
    # self.printMatchData()
    # self.printMatchTypes()

  def printPlayerData(self):
    log("RaspuinoDartGame::printPlayerData()")
    if self.playerData:
      log(json.dumps(self.playerData))
    else:
      log("empty")

  def printMatchData(self):
    log("RaspuinoDartGame::printMatchData()")
    if self.matchData:
      log(json.dumps(self.matchData))
    else:
      log("empty")

  def printMatchTypes(self):
    log("RaspuinoDartGame::printMatchTypes()")
    if self.matchTypes:
      log(json.dumps(self.matchTypes))
    else:
      log("empty")

  def prepareMatch(self):
    log("RaspuinoDartGame::prepareMatch()")
    if self.currentMatch == None:
      players = {}
      for (p, player) in self.playerData.items():
        players[p] = {"name": player["name"], "matches": len(player["matches"])}
      prepareMatchData = {"players": players, "matchtypes": self.matchTypes}
      self.fireEvent(broadcast("matchrequestdata" + json.dumps(prepareMatchData)))
    else:
      pass

  def startMatch(self, data):
    log("RaspuinoDartGame::startMatch({})".format(data))
    startdata = json.loads(data)
    if self.currentMatch == None and len(startdata["players"]) > 0:
      knuth_shuffle(startdata["players"])
      players = {}
      for p in xrange(len(startdata["players"])):
        players[int(p)] = {
          "id": int(startdata["players"][p]),
          "name": self.playerData[int(startdata["players"][p])]["name"],
          "done": False,
          "frames": [],
          "rank": 0,
          "score": 0,
          "info": []
        }
      self.currentMatch = RaspuinoDartMatch(self.matchTypes[int(startdata["type"])]["short"], self.matchTypes[int(startdata["type"])]["description"], players).register(self)
      self.currentMatch.clientData()
    else:
      pass

  def clearMatch(self):
    log("RaspuinoDartGame::clearMatch()")
    del self.currentMatch
    self.currentMatch = None
    self.fireEvent(broadcast("currentmatch {}"))

  def addPlayer(self, name):
    log("RaspuinoDartGame::addPlayer({})".format(name))
    goodToGo = True
    for (p, player) in self.playerData.items():
      if player["name"].lower() == name.lower():
        goodToGo = False
    if not name:
      goodToGo = False
    if goodToGo:
      self.playerData[len(self.playerData)] = {"id": len(self.playerData), "name": name, "joined": datetime.now().strftime("%Y%m%d-%H%M%S"), "matches": []}
      message = {"messagetitle": "New player", "messagetext": name + " has been added!"}
      self.fireEvent(broadcast("message" + json.dumps(message)))

  def receiveInput(self, source, data):
    log("RaspuinoDartGame::receiveInput({}, {})".format(source, data))
    if data.startswith("matchrequest"):
      self.prepareMatch()
    elif data.startswith("addplayer"):
      self.addPlayer(data.replace("addplayer", ""))
    elif data.startswith("startmatch"):
      self.startMatch(data.replace("startmatch", ""))
    elif data.startswith("endmatch"):
      self.clearMatch()
    elif data.startswith("darts"):
      if not self.currentMatch == None:
        self.currentMatch.addDart(data.replace("darts", ""))
    elif data.startswith("undo"):
      if not self.currentMatch == None:
        self.currentMatch.undoDart()
    elif data.startswith("clientdata"):
      if not self.currentMatch == None:
        self.currentMatch.clientData()

# #############################################################################
# websockets class

class RaspuinoDartEcho(Component):
  channel = "wsserver"

  # could add feature code to only allow one specific/authenticated client(s)

  def init(self):
    log("RaspuinoDartEcho::init")
    self.clients = {}

  def connect(self, socket, host, port):
    log("RaspuinoDartEcho::connect({}, {}, {})".format(id(socket), host, port))
    self.clients[socket] = {
      "host": host,
      "port": port,
    }
    self.fireEvent(write(socket, "welcome %s:%d, you're connection number %d" % (host, port, len(self.clients))))
    self.broadcast("%s:%d joined as number %d" % (host, port, len(self.clients)))
    self.fireEvent(receiveInput('web', "clientdata"))

  def disconnect(self, socket):
    log("RaspuinoDartEcho::disconnect({}) <= {}, {}".format(id(socket), host, port))
    print "%s:%s disconnected" % (self.clients[socket]["host"], self.clients[socket]["port"])
    for sock in self.clients:
      self.fireEvent(write(sock, "%s:%d left, with %d connections remaining" % (self.clients[socket]["host"], self.clients[socket]["port"], len(self.clients) - 1)))
    if socket in self.clients:
      del self.clients[socket]

  def read(self, socket, data):
    log("RaspuinoDartEcho::read({}, {})".format(id(socket), data))
    self.fireEvent(receiveInput('web', data))

  def broadcast(self, data):
    log("RaspuinoDartEcho::broadcast({})".format(data))
    for sock in self.clients:
      self.fireEvent(write(sock, data))

# #############################################################################
# server wrapper class

class RaspuinoDartServer(Server):
  def __init__(self):
    log("RaspuinoDartServer::__init__")
    Server.__init__(self, ("0.0.0.0", 8000))
    Static(docroot=".", defaults=['RaspuinoDart.html']).register(self)
    RaspuinoDartEcho().register(self)
    WebSocketsDispatcher("/websocket").register(self)

# #############################################################################
# serial board-connect class

# http://pydoc.net/Python/circuits/2.0.0/circuits.io.serial/
serial = tryimport("serial")
class RaspuinoDartBoard(Component):
  channel = 'serial'

  def __init__(self, port = '/dev/ttyACM0', baudrate = 115200, bufsize = 1, timeout = 0, channel = channel):
    log("RaspuinoDartBoard::__init__({})".format(port))
    super(RaspuinoDartBoard, self).__init__(channel = channel)
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
    log("RaspuinoDartBoard::read({})".format(self.serial_matrix[ord(data)]))
    self.fireEvent(receiveInput('board', 'darts' + self.serial_matrix[ord(data)]))
    self.flush()
    # for byte in data:
    #   self.fireEvent(receiveInput('board', 'darts' + self.serial_matrix[ord(byte)]))
    #   self.flush()

# #############################################################################
# Data-base connection

class RaspuinoDartDB(Component):
  def __init__(self):
    log("RaspuinoDartDB::__init__")
    Component.__init__(self)
    self.dbname = "RaspuinoDart.db"
    self.conn = sqlite3.connect(self.dbname)

    ini_players = [
      ("Sascha", "20170210-000000", ""),
      ("Heike" , "20170210-000000", ""),
      ("Michi" , "20170210-000000", ""),
      ("Jochen", "20170210-000000", ""),
    ]

    # self.matchData = {
    #   0: {"type": 0, "datetime": datetime.now().strftime("%Y%m%d-%H%M%S"), "players": [0, 2, 3], "history": []},
    #   1: {"type": 0, "datetime": datetime.now().strftime("%Y%m%d-%H%M%S"), "players": [3, 0, 2], "history": []}
    # }

    self.conn.execute("CREATE TABLE IF NOT EXISTS players(name TEXT, joined TEXT, matches TEXT)")

    self.conn.executemany('INSERT INTO players VALUES (?,?,?)', ini_players)
    # self.conn.execute("INSERT INTO players(name, joined, matches) VALUES ('Sascha', '20170210-000000', '0, 1')")
    for row in self.conn.execute("SELECT * FROM players"):
      log("{}".format(row))
    self.conn.close()

# #############################################################################
# global wrapper class

class RaspuinoDart(Component):
  def __init__(self):
    log("RaspuinoDart::__init__")
    Component.__init__(self)
    RaspuinoDartDB().register(self)
    RaspuinoDartGame().register(self)
    RaspuinoDartServer().register(self)
    RaspuinoDartBoard().register(self)

# #############################################################################
# the main execute

if __name__ == "__main__":
  m = RaspuinoDart()
  m.run()
