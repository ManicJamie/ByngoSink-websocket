#!/usr/bin/env python

import os
from typing import Optional
from websockets import ConnectionClosedError
from websockets.server import serve, WebSocketServerProtocol
import asyncio, json, logging
import time
from datetime import datetime
import ssl

import generators, boards
from rooms import *

_log = logging.getLogger("byngosink")
_log.propagate = False
formatter = logging.Formatter(fmt='%(asctime)s : %(name)s : %(levelname)-8s :: %(message)s')

streamHandler = logging.StreamHandler()
streamHandler.setFormatter(formatter)
_log.addHandler(streamHandler)

if not os.path.exists("./logs"): os.mkdir("./logs")

fileHandler = logging.FileHandler(f"./logs/{datetime.utcnow().isoformat('_', 'seconds').replace(':', '-')}_byngosink.log", mode="w")
fileHandler.setFormatter(formatter)
_log.addHandler(fileHandler)
_log.setLevel(logging.INFO)
#logging.getLogger("websockets.server").setLevel(logging.INFO)

class DecoratedWebsocket(WebSocketServerProtocol):
    """Provides outbound logging and utility methods"""
    def set_user(self, user: Room.User = None):
        self.user = user
    
    def clear_self_from_room(self) -> Optional[Room]:
        if "user" not in self.__dict__: return None
        room = self.user.room
        self.user.socket = None
        return room

    async def send(self, message, suppress_log = False):
        if not suppress_log: _log.info(f"OUT | {self.remote_address[0]} | {message}")
        _log.debug(f"OUT | {self.remote_address[0]} | {message}")
        await super().send(message)
    
    async def send_json(self, data: dict):
        _log.info(f"OUT | {self.remote_address[0]} | {data.get('verb', None)}: {', '.join(data.keys())}")
        await self.send(json.dumps(data), suppress_log=True)

rooms: dict[str, Room] = {}

async def LIST(websocket: DecoratedWebsocket, data):
    roomlist = {rid: {"name": r.name, "game": r.board.game, "board": r.board.name, 
                      "variant": r.board.generatorName, "count": len(r.users)}
                for rid, r in rooms.items() if len(r.users) > 0}
    await websocket.send_json({"verb": "LISTED", "list": roomlist})

async def GET_GENERATORS(websocket: DecoratedWebsocket, data):
    game = data["game"]
    gens = [{"name": gen.name, "count": gen.count} for gen in generators.ALL[game].values()]
    await websocket.send_json({"verb": "GENERATORS", "game": game, "generators": gens})

async def GET_GAMES(websocket: DecoratedWebsocket, data):
    games = list(generators.ALL.keys())
    await websocket.send_json({"verb": "GAMES", "games": games})

async def GET_BOARDS(websocket: DecoratedWebsocket, data):
    games = list(boards.ALIASES.keys())
    await websocket.send_json({"verb": "BOARDS", "boards": games})

async def OPEN(websocket: DecoratedWebsocket, data):
    user_name = data["username"]
    room = Room(data["roomName"], data["game"], data["generator"], data["board"], data["seed"])
    user_id = room.add_user(user_name, websocket)
    rooms[room.id] = room
    
    await websocket.send_json({"verb": "OPENED", "roomId": room.id, "userId": user_id})

async def JOIN(websocket: DecoratedWebsocket, data):
    room_id = data["roomId"]
    if room_id not in rooms:
        await websocket.send('{"verb": "NOTFOUND"}')
        return
    room = rooms[room_id]
    user_id = room.add_user(data["username"], websocket)

    await websocket.send_json({"verb": "JOINED", "userId": user_id, "roomName": room.name, 
                               "boardMin": room.board.get_minimum_view(), 
                               "teamColours": {id:team.colour for id, team in room.teams.items()}})
    await room.alert_player_changes()

async def REJOIN(websocket: DecoratedWebsocket, data):
    user_id = data["userId"]
    room_id = data["roomId"]
    if room_id not in rooms:
        await websocket.send('{"verb": "NOTFOUND"}')
        return
    room = rooms[room_id]
    if user_id not in room.users:
        await websocket.send('{"verb": "NOAUTH"}')
        return
    
    user = room.users[user_id]
    user.change_socket(websocket)
    await websocket.send_json({"verb": "REJOINED", "roomName": room.name, "boardMin": room.board.get_team_view(user.teamId),
                                "teamId": user.teamId or "", "teamColours": {id:team.colour for id, team in room.teams.items()}})
    await room.alert_player_changes()

async def EXIT(websocket: DecoratedWebsocket, data):
    user_id = data["userId"]
    room_id = data["roomId"]
    if room_id not in rooms:
        await websocket.send('{"verb": "NOTFOUND"}')
        return
    room = rooms[room_id]
    user = room.users.pop(user_id, None)
    if user is None:
        await websocket.send('{"verb": "NOAUTH"}')
        return
    
    for team in room.teams.values():
        if team.id == user.teamId:
            team.members.remove(user)
            await room.alert_player_changes()

async def CREATE_TEAM(websocket: DecoratedWebsocket, data):
    room_id = data["roomId"]
    name = data["name"]
    colour = data["colour"]
    if room_id not in rooms:
        await websocket.send('{"verb": "NOTFOUND"}')
        return
    room = rooms[room_id]
    user = room.get_user_by_socket(websocket)
    if user is None:
        await websocket.send('{"verb": "NOAUTH"}')
        return
    if user.teamId is not None and user.teamId in room.teams: # If user is already in team, remove them from this team
        room.teams[user.teamId].members.remove(user)

    team = room.create_team(name, colour)
    team.add_user(user)
    user.teamId = team.id
    user.spectate = False

    await websocket.send_json({"verb": "TEAM_CREATED", "teamId": team.id,
                               "board": room.board.get_team_view(user.teamId), 
                               "teamColours": {id:team.colour for id, team in room.teams.items()}})
    await room.alert_player_changes()

async def JOIN_TEAM(websocket: DecoratedWebsocket, data):
    room_id = data["roomId"]
    team_id = data["teamId"]
    if room_id not in rooms:
        await websocket.send('{"verb": "NOTFOUND"}')
        return
    room = rooms[room_id]
    user = room.get_user_by_socket(websocket)
    if user is None:
        await websocket.send('{"verb": "NOAUTH"}')
        return
    team = room.teams.get(team_id, None)
    if team is None:
        await websocket.send('{"verb": "NOTFOUND"}')
        return
    if user.teamId is not None and user.teamId in room.teams: # If user is already in team, remove them from this team
        room.teams[user.teamId].members.remove(user)
    team.add_user(user)
    user.teamId = team.id
    user.spectate = False
    await websocket.send_json({"verb": "TEAM_JOINED", "board": room.board.get_team_view(user.teamId), "teamId": team.id,
                               "teamColours": {id:team.colour for id, team in room.teams.items()}})
    await room.alert_player_changes()

async def LEAVE_TEAM(websocket: DecoratedWebsocket, data):
    room_id = data["roomId"]
    if room_id not in rooms:
        await websocket.send('{"verb": "NOTFOUND"}')
        return
    room = rooms[room_id]
    user = room.get_user_by_socket(websocket)
    if user is None:
        await websocket.send('{"verb": "NOAUTH"}')
        return
    for team in room.teams.values():
        if team.id == user.teamId:
            team.members.remove(user)
            await websocket.send('{"verb": "TEAM_LEFT"}')
            await room.alert_player_changes()
            return

async def get_goal_params(websocket: DecoratedWebsocket, data):
    room_id = data["roomId"]
    goal_id = data["goalId"]
    if room_id not in rooms:
        await websocket.send('{"verb": "NOTFOUND"}')
        return None
    room = rooms[room_id]
    user = room.get_user_by_socket(websocket)
    if user is None:
        await websocket.send('{"verb": "NOAUTH"}')
        return None
    if user.teamId is None:
        await websocket.send('{"verb": "NOTEAM"}')
        return None

    return (user, room, int(goal_id))
    
async def MARK(websocket: DecoratedWebsocket, data):
    params = await get_goal_params(websocket, data)
    if params is None: return
    user, room, goal_id = params
    
    # TODO: Communicate failure in e.g. invasion, lockout, etc.
    if room.board.mark(goal_id, user.teamId):
        await websocket.send_json({"verb": "MARKED", "goalId": goal_id})
        await room.alert_board_changes()
    else:
        await websocket.send_json({"verb": "NOMARK", "goalId": goal_id})
    
async def UNMARK(websocket: DecoratedWebsocket, data):
    params = await get_goal_params(websocket, data)
    if params is None: return
    user, room, goal_id = params

    room.board.unmark(int(goal_id), user.teamId)
    await websocket.send_json({"verb": "UNMARKED", "goalId": goal_id})
    await room.alert_board_changes()

async def SPECTATE(websocket: DecoratedWebsocket, data):
    room_id = data.get("roomId", None)
    if room_id not in rooms:
        await websocket.send('{"verb": "NOTFOUND"}')
        return None
    room = rooms.get(room_id)
    user = room.get_user_by_socket(websocket)
    if user is None:
        await websocket.send('{"verb": "NOAUTH"}')
        return None
    
    if user.spectate == 0:
        user.spectate = 1
        room.spectators.add_user(user)
        if user.teamId is not None and user.teamId in room.teams:
            room.teams[user.teamId].members.remove(user)
        user.teamId = room.spectators.id

        await user.socket.send_json({"verb": "UPDATE", "board": room.board.get_spectator_view(), 
                            "teamColours": {id:team.colour for id, team in room.teams.items()}})
    elif user.spectate == 1:
        user.spectate = 2
        await user.socket.send_json({"verb": "UPDATE", "board": room.board.get_full_view(), 
                        "teamColours": {id:team.colour for id, team in room.teams.items()}})
    else:
        return # do nothing if already at max spectator level
    
    await room.alert_player_changes()

async def TIMELAPSE(websocket: DecoratedWebsocket, data):
    room_id = data.get("roomId", None)
    if room_id not in rooms:
        await websocket.send('{"verb": "NOTFOUND"}')
        return None
    room = rooms.get(room_id)
    user = room.get_user_by_socket(websocket)
    if user is None:
        await websocket.send('{"verb": "NOAUTH"}')
        return None
    
    if user.spectate == 0:
        await user.socket.send_json({"verb": "NOAUTH"})
    else:
        await user.socket.send_json({"verb": "TIMELAPSE", "history": room.board.markHistory})

HANDLERS = {"LIST": LIST,
            "OPEN": OPEN,
            "JOIN": JOIN,
            "REJOIN": REJOIN,
            "EXIT": EXIT,
            "MARK": MARK,
            "UNMARK": UNMARK,
            "GET_GENERATORS": GET_GENERATORS,
            "GET_GAMES": GET_GAMES,
            "GET_BOARDS": GET_BOARDS,
            "CREATE_TEAM": CREATE_TEAM,
            "JOIN_TEAM": JOIN_TEAM,
            "LEAVE_TEAM": LEAVE_TEAM,
            "SPECTATE": SPECTATE,
            }

async def remove_websocket(websocket: DecoratedWebsocket):
    for room in rooms.values():
        update = False
        for user in room.users.values():
            if user.socket == websocket:
                user.socket = None
                update = True
        if update:
            await room.alert_player_changes()

async def process(websocket: DecoratedWebsocket): 
    websocket.__class__ = DecoratedWebsocket # Websocket is passed as a WebSocketClientProtocol, but upgraded
    addr = websocket.remote_address[0]
    _log.info(f"CON | {addr}")
    try:
        async for received in websocket: 
            try:
                _log.info(f"IN  | {addr} | {received}")
                data = json.loads(received)
                if data["verb"] not in HANDLERS:
                    _log.warning(f"Bad verb received | {data['verb']}")
                    continue
                await HANDLERS[data["verb"]](websocket, data)
            except Exception as e:
                await websocket.send_json({"verb": "ERROR", "message": f"Server Error: {e.__repr__()}"})
                _log.error(e, exc_info=True)
    except ConnectionClosedError as e:
        _log.warning(f"!DIS | {addr}")
        _log.debug(e, exc_info=True)
    
    _log.info(f"DIS | {addr}")
    exitRoom = websocket.clear_self_from_room()
    if exitRoom is not None: await exitRoom.alert_player_changes()

CERTS_PATH = "/etc/letsencrypt/live/byngosink-ws.manicjamie.com"
FULL_CHAIN = f"{CERTS_PATH}/fullchain.pem"
PRIV_KEY = f"{CERTS_PATH}/privkey.pem"

if os.path.exists(FULL_CHAIN) and os.path.exists(PRIV_KEY): # Do SSL if the certificates exist, otherwise warn
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    ssl_context.load_cert_chain(FULL_CHAIN, PRIV_KEY)
else:
    _log.warning("Certs not found: SSL not enabled!")
    ssl_context = None

async def main():
    async with serve(process, "0.0.0.0", 555, ssl=ssl_context):
        await asyncio.Future() # Run forever

if __name__ == "__main__":
    asyncio.run(main())