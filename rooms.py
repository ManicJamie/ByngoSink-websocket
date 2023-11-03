from uuid import uuid4
from time import time

COLOURS = {
    "Red": "#FF0000",
    "Orange": "#",
    "Yellow": "",
    "Purple": "",

}

class Room():
    class User():
        def __init__(self, name, websocket) -> None:
            self.name = name 
            self.socket = websocket
            self.id = str(uuid4())
            self.connected = False
            self.teamId = None

        def change_socket(self, websocket):
            self.socket = websocket
    
    class Team():
        def __init__(self, colour) -> None:
            self.id = str(uuid4())
            self.colour: str = colour
    
    def __init__(self, board, game, name) -> None:
        self.board = board
        self.game = game
        self.name = name
        start_team = Room.Team("Red")
        self.teams: dict[str, Room.Team] = {start_team.id: start_team}
        self.users: dict[str, Room.User] = {}
        self.id = str(uuid4())
        self.created = int(time())
        self.touch()
    
    def add_user(self, user_name: str, socket) -> str:
        user = Room.User(user_name, socket)
        self.users[user.id] = user
        user.connected = True
        return user.id

    def pop_user(self, user_id):
        return self.users.pop(user_id)
    
    def touch(self):
        self.touched = int(time())