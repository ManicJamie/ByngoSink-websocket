from random import random
from uuid import uuid4
from time import time
import logging

from boards import create_board
from generators import get_generator

from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    from socket_handler import DecoratedWebsocket
    T_WEBSOCKET = Union[DecoratedWebsocket, None]

_log = logging.getLogger("byngosink")

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
        def __init__(self, name: str, room, websocket: "T_WEBSOCKET" = None) -> None:
            self.id = str(uuid4())
            self.name = name
            self.socket = websocket
            self.room = room
            self.teamId = None
            self.spectate = 0
            if websocket is not None:
                websocket.set_user(self)

        def change_socket(self, websocket: "DecoratedWebsocket"):
            self.socket = websocket
            websocket.set_user(self)
        
        def view(self):
            return {"name": self.name, "connected": self.socket is not None, "teamId": self.teamId}
    
    class Team():
        def __init__(self, name, colour) -> None:
            self.id = str(uuid4())
            self.name = name
            self.colour: str = colour
            self.members: list[Room.User] = []

        def add_user(self, user): self.members.append(user)
        def remove_user(self, user): self.members.remove(user)
        
        def view(self):
            return {"id": self.id, "name": self.name, "colour": self.colour, "members": [m.view() for m in self.members]}
    
    def __init__(self, name, game, generator_str, board_str, seed) -> None:
        self.id = str(uuid4())
        self.name = name
        self.spectators = Room.Team("spectator", "#FFFFFF")
        self.teams: dict[str, Room.Team] = {}
        self.users: dict[str, Room.User] = {}
        self.generate_board(game, generator_str, board_str, seed)
        self.created = int(time())
        self.touch()
    
    def add_user(self, user_name: str, socket=None) -> str:
        user = Room.User(user_name, self, socket)
        self.users[user.id] = user
        return user.id

    def get_user_by_socket(self, websocket: "DecoratedWebsocket"):
        for user in self.users.values():
            if websocket == user.socket: return user
        return None
    
    def touch(self): self.touched = int(time())
    
    def generate_board(self, game, generator_str, board_str, seed):
        if (seed == ""): seed = str(random())
        generator = get_generator(game, generator_str)
        self.board = create_board(board_str, generator, seed)
        self.languages = generator.languages
        self.touch()
    
    def create_team(self, name, colour):
        team = self.Team(name, colour)
        self.teams[team.id] = team
        return team
    
    def connected_users(self) -> dict[str, User]:
        out = {}
        for k, u in self.users.items():
            if u.socket is not None: out[k] = u
        return out

    async def alert_board_changes(self):
        for user in self.users.values():
            if user.socket is not None:
                if user.socket.closed: user.socket = None
                else:
                    if user.spectate == 0:
                        await user.socket.send_json({"verb": "UPDATE", "board": self.board.get_team_view(user.teamId),
                                                    "teamColours": {id: team.colour for id, team in self.teams.items()}})
                    elif user.spectate == 1:
                        await user.socket.send_json({"verb": "UPDATE", "board": self.board.get_spectator_view(),
                                                    "teamColours": {id: team.colour for id, team in self.teams.items()}})
                    else:  # user.spectate == 2
                        await user.socket.send_json({"verb": "UPDATE", "board": self.board.get_full_view(),
                                                    "teamColours": {id: team.colour for id, team in self.teams.items()}})
    
    async def alert_player_changes(self):
        usersData = [user.view() for user in self.users.values()]

        for user in self.connected_users().values():
            if user.socket.closed: user.socket = None
            else:
                await user.socket.send_json({"verb": "MEMBERS", "members": usersData,
                                             "teams": {id: team.view() for id, team in self.teams.items()}})
