#!/usr/bin/env python

from websockets.server import serve, WebSocketServerProtocol
import asyncio, uuid, json, logging
import time

import generators, boards, goals
from rooms import *

logging.basicConfig(level=logging.DEBUG, format='%(message)s')
_log = logging.getLogger("bingosink")
_log.setLevel(logging.INFO)
logging.getLogger("websockets.server").setLevel(logging.INFO)

rooms: dict[str, Room] = {}

async def LIST(websocket: WebSocketServerProtocol, data):
    roomlist = {rid: {"name": r.name, "game": r.board.game, "board": r.board.name, 
                      "variant": r.board.generatorName, "count": len(r.users)}
                for rid, r in rooms.items()}
    await websocket.send(json.dumps({"verb": "LISTED", "list": roomlist}))

async def MARK(websocket: WebSocketServerProtocol, data):
    pass

async def GET_GENERATORS(websocket: WebSocketServerProtocol, data):
    game = data["game"]
    gens = [{"name": gen.name, "small": gen.count < 169} for gen in generators.ALL[game].values()]
    await websocket.send(json.dumps({"verb": "GENERATORS", "game": game, "generators": gens}))

async def GET_GAMES(websocket: WebSocketServerProtocol, data):
    games = list(generators.ALL.keys())
    await websocket.send(json.dumps({"verb": "GAMES", "games": games}))

async def OPEN(websocket: WebSocketServerProtocol, data):
    user_name = data["username"]
    room = Room(data["roomName"], data["game"], data["generator"], data["board"], data["seed"])
    user_id = room.add_user(user_name, websocket)
    rooms[room.id] = room
    
    await websocket.send(json.dumps({"verb": "OPENED", "roomId": room.id, "userId": user_id}))

async def JOIN(websocket: WebSocketServerProtocol, data):
    room_id = data["roomId"]
    if room_id not in rooms:
        await websocket.send('{"verb": "NOTFOUND"}')
        return
    room = rooms[room_id]
    user_id = room.add_user(data["username"], websocket)

    await websocket.send(json.dumps({"verb": "JOINED", "userId": user_id, "roomName": room.name, "boardMin": room.board.get_minimum_view()}))
    await room.alert_player_changes()

async def REJOIN(websocket: WebSocketServerProtocol, data):
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
    await websocket.send(json.dumps({"verb": "REJOINED", "roomName": room.name, "boardMin": room.board.get_minimum_view()}))
    await room.alert_player_changes()

async def EXIT(websocket: WebSocketServerProtocol, data):
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

async def CREATE_TEAM(websocket: WebSocketServerProtocol, data):
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
    team = room.create_team(name, colour)
    team.add_user(user.id)
    user.teamId = team.id
    await websocket.send(json.dumps({"verb": "TEAM_CREATED", "team_id": team.id}))
    await room.alert_player_changes()

async def JOIN_TEAM(websocket: WebSocketServerProtocol, data):
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
    team.add_user(user)
    await websocket.send('{"verb": "TEAM_JOINED"}')
    await room.alert_player_changes()

async def LEAVE_TEAM(websocket: WebSocketServerProtocol, data):
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

async def A(websocket: WebSocketServerProtocol, data): pass
async def A(websocket: WebSocketServerProtocol, data): pass

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

async def remove_websocket(websocket):
    for room in rooms.values():
        update = False
        for user in room.users.values():
            if user.socket == websocket:
                user.connected = False
                update = True
        if update:
            await room.alert_player_changes()

async def process(websocket: WebSocketServerProtocol):
    _log.info(f"New websocket connected from {websocket.remote_address}")
    async for received in websocket:
        try:
            _log.info(f"{websocket.remote_address} | {received}")
            data = json.loads(received)
            if data["verb"] not in HANDLERS:
                _log.warning(f"Bad verb received | {data['verb']}")
                continue
            await HANDLERS[data["verb"]](websocket, data)
        except Exception as e:
            await websocket.send(json.dumps({"verb": "ERROR", "message": f"Server Error: {e.__repr__()}"}))
            raise e
    _log.info(f"Websocket from {websocket.remote_address} disconnected")
    await remove_websocket(websocket)

async def main():
    async with serve(process, "localhost", 555):
        await asyncio.Future() # Run forever

if __name__ == "__main__":
    asyncio.run(main())