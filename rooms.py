from random import random
from uuid import uuid4
from time import time
from websockets import ConnectionClosed
import json, asyncio, logging

from boards import create_board
from generators import get_generator

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from generators import T_GENERATOR
    from socket_handler import DecoratedWebsocket

_log = logging.getLogger("bingosink")

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
        def __init__(self, name: str, websocket: "DecoratedWebsocket" = None) -> None:
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
        def __init__(self, name, colour) -> None:
            self.id = str(uuid4())
            self.name = name
            self.colour: str = colour
            self.members:list[Room.User] = []

        def add_user(self, user): self.members.append(user)
        def remove_user(self, user): self.members.remove(user)
        
        def view(self):
            return {"id": self.id, "name": self.name, "colour": self.colour, "members": [m.view() for m in self.members]}
    
    class Message():
        def __init__(self, origin, content) -> None:
            self.origin = origin
            self.content = content
    
    def __init__(self, name, game, generator_str, board_str, seed) -> None:
        self.id = str(uuid4())
        self.name = name
        self.teams: dict[str, Room.Team] = {}
        self.users: dict[str, Room.User] = {}
        if (seed == ""): seed = str(random())
        self.generate_board(game, generator_str, board_str, seed)
        self.created = int(time())
        self.touch()
    
    def add_user(self, user_name: str, socket=None) -> str:
        user = Room.User(user_name, socket)
        self.users[user.id] = user
        user.connected = True
        return user.id

    def get_user_by_socket(self, websocket: "DecoratedWebsocket"):
        for user in self.users.values():
            if websocket == user.socket: return user
        return None
    
    def pop_user(self, user_id): return self.users.pop(user_id)
    def touch(self): self.touched = int(time())
    
    def generate_board(self, game, generator_str, board_str, seed):
        self.board = create_board(board_str, get_generator(game, generator_str), seed)
        self.touch()
    
    def create_team(self, name, colour):
        team = self.Team(name, colour)
        self.teams[team.id] = team
        return team
    
    async def alert_board_changes(self):
        for user in self.users.values():
            if user.socket is not None:
                if user.socket.closed: user.socket = None
                else:
                    await user.socket.send_json({"verb": "UPDATE", "board": self.board.get_team_view(user.teamId), 
                                                "teamColours": {id:team.colour for id, team in self.teams.items()}})
    
    async def alert_player_changes(self):
        usersData = [user.view() for user in self.users.values()]

        for user in self.users.values():
            if user.socket is not None:
                if user.socket.closed: user.socket = None
                else:
                    await user.socket.send_json({"verb": "MEMBERS", "members": usersData,
                                                 "teams": {id:team.view() for id, team in self.teams.items()}})