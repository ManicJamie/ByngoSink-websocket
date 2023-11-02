#!/usr/bin/env python

from websockets.server import serve, WebSocketServerProtocol
import asyncio, uuid, json, logging
from enum import IntEnum
import time

import generators, boards, goal_types

_log = logging.getLogger("bingosink")
_log.setLevel(logging.INFO)

class BoardEnum(IntEnum):
    BINGO=0,
    LOCKOUT=1,
    EXPLORATION=2,
    GTTOS=3,
    ROGUELIKE=4

    @classmethod
    def all(cls):
        return [int(member) for member in cls]

class GameEnum(IntEnum):
    HOLLOW_KNIGHT=0

    @classmethod
    def all(cls):
        return [int(member) for member in cls]

class Room():
    class User():
        def __init__(self, name, websocket) -> None:
            self.name = name 
            self.socket = websocket
            self.id = str(uuid.uuid4())
            self.connected = False

        def change_socket(self, websocket):
            self.socket = websocket
    
    def __init__(self, board, w, h, game, room) -> None:
        self.board = BoardEnum(board)
        self.width = int(w)
        self.height = int(h)
        self.game = GameEnum(game)
        self.name = room
        self.users: dict[str, Room.User] = {}
        self.id = str(uuid.uuid4())
        self.created = int(time.time())
        self.touch()
    
    def add_user(self, user_name: str, socket) -> str:
        user = Room.User(user_name, socket)
        self.users[user.id] = user
        user.connected = True
        return user.id

    def pop_user(self, user_id):
        return self.users.pop(user_id)
    
    def touch(self):
        self.touched = int(time.time())

rooms: dict[str, Room] = {}

async def process(websocket: WebSocketServerProtocol):
    async for received in websocket:
        try:
            _log.info(f"{websocket.remote_address} | {received}")
            data = json.loads(received)
            match data["verb"]:
                case "LIST":
                    roomlist = {rid:{"name": r.name, "game": r.game, "board": r.board, "count": len(r.users)}
                                 for rid, r in rooms.items()}
                    await websocket.send(json.dumps(roomlist))
                case "OPEN":
                    user_name = data["username"]
                    room = Room(data["boardType"], data["width"], data["height"],
                                 data["gameEnum"], data["roomName"])
                    user_id = room.add_user(user_name, websocket)
                    rooms[room.id] = room
                    
                    await websocket.send(json.dumps({"verb": "OPENED", "roomId": room.id, "userId": user_id}))
                case "JOIN":
                    pass
                case "REJOIN":
                    user_id = data["userId"]
                    room_id = data["roomId"]
                    room = rooms[room_id]
                    if user_id in room.users:
                        await websocket.send(json.dumps({"verb": "REJOINED", "roomId": room.id, "userId": user_id}))
                case "MARK":
                    pass
        except Exception as e:
            await websocket.send(json.dumps({"verb": "ERROR", "message": str(e.args)}))
            raise e

async def main():
    async with serve(process, "localhost", 555):
        await asyncio.Future() # Run forever

if __name__ == "__main__":
    asyncio.run(main())