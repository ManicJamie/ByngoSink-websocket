#!/usr/bin/env python

from websockets.server import serve, WebSocketServerProtocol
import asyncio, uuid, json, logging
from enum import IntEnum, StrEnum
import time

import generators, boards, goal_types
from rooms import *

_log = logging.getLogger("bingosink")
logging.getLogger().setLevel(logging.INFO)

rooms: dict[str, Room] = {}

async def process(websocket: WebSocketServerProtocol):
    async for received in websocket:
        try:
            logging.info(f"{websocket.remote_address} | {received}")
            data = json.loads(received)
            match data["verb"]:
                case "LIST":
                    roomlist = {rid:{"name": r.name, "game": r.game, "board": r.board, "count": len(r.users)}
                                 for rid, r in rooms.items()}
                    await websocket.send(json.dumps(roomlist))
                case "OPEN":
                    user_name = data["username"]
                    room = Room(data["board"],
                                 data["game"], data["roomName"])
                    user_id = room.add_user(user_name, websocket)
                    rooms[room.id] = room
                    
                    await websocket.send(json.dumps({"verb": "OPENED", "roomId": room.id, "userId": user_id}))
                case "JOIN":
                    room = rooms[data["roomId"]]
                    user_id = room.add_user(data["username"], websocket)

                    await websocket.send(json.dumps({"verb": "JOINED", "userId": user_id}))
                case "REJOIN":
                    user_id = data["userId"]
                    room_id = data["roomId"]
                    room = rooms[room_id]
                    if user_id in room.users:
                        await websocket.send(json.dumps({"verb": "REJOINED", "roomId": room.id, "userId": user_id}))
                case "MARK":
                    pass
                case "GET_GENERATORS":
                    game = data["game"]
                    gens = list(generators.ALL[game].keys())
                    await websocket.send(json.dumps({"verb": "GENERATORS", "game": game, "generators": gens}))
                case "GET_GAMES":
                    games = list(generators.ALL.keys())
                    await websocket.send(json.dumps({"verb": "GAMES", "games": games}))
        except Exception as e:
            await websocket.send(json.dumps({"verb": "ERROR", "message": str(e.args)}))
            raise e

async def main():
    async with serve(process, "localhost", 555):
        await asyncio.Future() # Run forever

if __name__ == "__main__":
    asyncio.run(main())