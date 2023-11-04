from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from generators import T_GENERATOR
    from goals import T_GOAL

class Board():
    """Basic unbiased board"""
    name = "Board"
    def __init__(self, w, h, generator: "T_GENERATOR", seed: str) -> None:
        self.width = w
        self.height = h
        self.game = generator.game
        self.generatorName = generator.name
        self.seed = seed
        self.goals: list[T_GOAL] = generator.get(seed, w*h)
        self.marks: dict[str, set] = {} # {Teamid : {goals}}
    
    def get_minimum_view(self) -> dict:
        """Provides a minimum amount of data on the board for display (used on join)"""
        return {"type": self.name, "width": self.width, "height": self.height,
                "game": self.game, "generatorName": self.generatorName}
    
    def get_team_view(self, teamId) -> dict:
        """Provides a view on the board for a given user"""
        return self.get_dict()
    
    def mark(self, index, teamid) -> bool:
        if teamid not in self.marks: self.marks[teamid] = {index}
        elif index in self.marks[teamid]: return False
        else: self.marks[teamid].add(index)
        return True
    
    def unmark(self, index, teamid) -> bool:
        if teamid not in self.marks: 
            return False
        elif index not in self.marks[teamid]: 
            return False
        else: 
            self.marks[teamid].remove(index)
        return False

    def get_dict(self) -> dict:
        return {"type": str(type(self)),
                "width": self.width,
                "height": self.height,
                "goals": self.goals,
                "marks": self.marks}

class Bingo(Board):
    """Alias for 5x5 board"""
    name = "Non-Lockout"
    def __init__(self, generator: "T_GENERATOR", seed) -> None:
        super().__init__(5, 5, generator, seed)

class Lockout(Bingo):
    """Basic lockout bingo board"""
    name = "Lockout"
    def mark(self, index: int, teamid: str) -> bool:
        if teamid not in self.marks: 
            self.marks[teamid] = {}

        if index in self.marks[teamid]: 
            return False
        else: 
            print(*self.marks.values())
            allmarked = set().union(*self.marks.values())
            if index in allmarked: 
                return False
            self.marks[teamid].add(index)
        return True

class Exploration(Board):
    """13x13 board with marks hidden between teams and only adjacent goals displayed."""
    name = "Exploration"
    def __init__(self, generator: "T_GENERATOR", seed) -> None:
        super().__init__(13, 13, generator, seed)
    
    def adjacent(self, i):
        pass

ALIASES = {
    "Non-Lockout": Bingo,
    "Lockout": Lockout,
    "Exploration": Exploration
}

def create_board(boardstr, generator: "T_GENERATOR", seed) -> Board:
    return ALIASES[boardstr](generator, seed)