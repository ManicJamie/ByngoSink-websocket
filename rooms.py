from random import random
from uuid import uuid4
from time import time
from websockets import ConnectionClosed, WebSocketServerProtocol
import json, asyncio, logging

from boards import create_board
from generators import get_generator

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from generators import T_GENERATOR

COLOURS = {
    "Pink": "#cc6e8f",
    "Red": "#FF0000",
    "Orange": "#FFA500",
    "Brown": "#8B4513",
    "Yellow": "#FFFF00",
    "Green": "#00FF00",
    "Teal": "#008080",
    "Blue": "#00FFFF",
    "Navy": "#000080",
    "Purple": "#9400D3"
}

class Room():
    class User():
        def __init__(self, name: str, websocket: WebSocketServerProtocol) -> None:
            self.name = name 
            self.socket = websocket
            self.id = str(uuid4())
            self.connected = False
            self.teamId = None

        def change_socket(self, websocket):
            self.socket = websocket
        
        def view(self):
            return {"name": self.name, "connected": self.connected, "teamId": self.teamId}
    
    class Team():
        def __init__(self, colour) -> None:
            self.id = str(uuid4())
            self.colour: str = colour
    
    def __init__(self, name, game, generator_str, board_str, seed) -> None:
        self.id = str(uuid4())
        self.name = name
        start_team = Room.Team("Red")
        self.teams: dict[str, Room.Team] = {start_team.id: start_team}
        self.users: dict[str, Room.User] = {}
        if (seed == ""): seed = str(random())
        self.generate_board(game, generator_str, board_str, seed)
        self.created = int(time())
        self.touch()
    
    def add_user(self, user_name: str, socket) -> str:
        user = Room.User(user_name, socket)
        self.users[user.id] = user
        user.connected = True
        return user.id
    
    def pop_user(self, user_id): return self.users.pop(user_id)
    def touch(self): self.touched = int(time())
    
    def generate_board(self, game, generator_str, board_str, seed):
        self.board = create_board(board_str, get_generator(game, generator_str), seed)
    
    async def alert_board_changes(self):
        for user in self.users.values():
            await user.socket.send(json.dumps({"verb": "SHARE", "board": self.board.get_team_view(user.id)}))
    
    async def alert_player_changes(self):
        usersData = [user.view() for user in self.users.values()]

        for user in self.users.values():
            if user.socket is not None:
                try:
                    await user.socket.send(json.dumps({"verb": "MEMBERS", "members": usersData}))
                except ConnectionClosed as e:
                    logging.error(f"Connection closed! {e.__repr__()}")
                    user.socket = None