#!/usr/bin/env python

import pathlib
from typing import Optional
from websockets.server import serve, WebSocketServerProtocol
import asyncio, uuid, json, logging
import time
import ssl

import generators, boards, goals
from rooms import *

_log = logging.getLogger("bingosink")
_log.propagate = False
formatter = logging.Formatter(fmt='%(asctime)s : %(name)s : %(levelname)-8s :: %(message)s')

streamHandler = logging.StreamHandler()
streamHandler.setFormatter(formatter)
_log.addHandler(streamHandler)

fileHandler = logging.FileHandler("byngosink.log")
fileHandler.setFormatter(formatter)
_log.addHandler(fileHandler)
_log.setLevel(logging.INFO)
#logging.getLogger("websockets.server").setLevel(logging.INFO)

class DecoratedWebsocket(WebSocketServerProtocol):
    """Provides outbound logging and utility methods"""
    def set_user(self, user: Room.User = None):
        self.user = user
    
    def clear_self_from_room(self) -> bool:
        if self.user is not None:
            self.user.socket = None
            return True
        return False

    async def send(self, message):
        _log.info(f"OUT | {self.remote_address[0]} | {message}")
        await super().send(message)
    
    async def send_json(self, data: dict):
        await self.send(json.dumps(data))

rooms: dict[str, Room] = {}

async def LIST(websocket: DecoratedWebsocket, data):
    roomlist = {rid: {"name": r.name, "game": r.board.game, "board": r.board.name, 
                      "variant": r.board.generatorName, "count": len(r.users)}
                for rid, r in rooms.items()}
    await websocket.send_json({"verb": "LISTED", "list": roomlist})

async def GET_GENERATORS(websocket: DecoratedWebsocket, data):
    game = data["game"]
    gens = [{"name": gen.name, "small": gen.count < 169} for gen in generators.ALL[game].values()]
    await websocket.send_json({"verb": "GENERATORS", "game": game, "generators": gens})

async def GET_GAMES(websocket: DecoratedWebsocket, data):
    games = list(generators.ALL.keys())
    await websocket.send_json({"verb": "GAMES", "games": games})

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
    
    room.users[user_id].change_socket(websocket)
    await websocket.send_json({"verb": "REJOINED", "roomName": room.name, "boardMin": room.board.get_team_view(room.users[user_id].teamId),
                                "teamColours": {id:team.colour for id, team in room.teams.items()}})
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
    if user.teamId is not None: # If user is already in team, remove them from this team
        room.teams[user.teamId].members.remove(user)

    team = room.create_team(name, colour)
    team.add_user(user)
    user.teamId = team.id

    await websocket.send_json({"verb": "TEAM_CREATED", "team_id": team.id,
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
    if user.teamId is not None: # If user is already in team, remove them from this team
        room.teams[user.teamId].members.remove(user)
    team.add_user(user)
    user.teamId = team.id
    await websocket.send_json({"verb": "TEAM_JOINED", "board": room.board.get_team_view(user.teamId), 
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

async def MARK(websocket: DecoratedWebsocket, data):
    room_id = data["roomId"]
    goal_id = data["goalId"]
    if room_id not in rooms:
        await websocket.send('{"verb": "NOTFOUND"}')
        return
    room = rooms[room_id]
    user = room.get_user_by_socket(websocket)
    if user is None:
        await websocket.send('{"verb": "NOAUTH"}')
        return
    if user.teamId is None:
        await websocket.send('{"verb": "NOTEAM"}')
        return
    
    room.board.mark(int(goal_id), user.teamId)
    await websocket.send_json({"verb": "MARKED", "goalId": goal_id})
    await room.alert_board_changes()

HANDLERS = {"LIST": LIST,
            "OPEN": OPEN,
            "JOIN": JOIN,
            "REJOIN": REJOIN,
            "EXIT": EXIT,
            "MARK": MARK,
            "GET_GENERATORS": GET_GENERATORS,
            "GET_GAMES": GET_GAMES,
            "CREATE_TEAM": CREATE_TEAM,
            "JOIN_TEAM": JOIN_TEAM,
            "LEAVE_TEAM": LEAVE_TEAM,
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
    _log.info(f"CON | {websocket.remote_address[0]} | {websocket.remote_address[1]}")
    async for received in websocket:
        try:
            _log.info(f"IN  | {websocket.remote_address[0]} | {received}")
            data = json.loads(received)
            if data["verb"] not in HANDLERS:
                _log.warning(f"Bad verb received | {data['verb']}")
                continue
            await HANDLERS[data["verb"]](websocket, data)
        except Exception as e:
            await websocket.send_json({"verb": "ERROR", "message": f"Server Error: {e.__repr__()}"})
            _log.error(e, exc_info=True)
    _log.info(f"DIS | {websocket.remote_address[0]} | {websocket.remote_address[1]}")
    websocket.clear_self_from_room()
    await remove_websocket(websocket)

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain("cert.pem", "cert.pem")

async def main():
    async with serve(process, "localhost", 555, ssl=ssl_context):
        await asyncio.Future() # Run forever

if __name__ == "__main__":
    asyncio.run(main())