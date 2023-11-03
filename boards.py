from generators import *

class Board():
    """Basic unbiased board"""
    def __init__(self, w, h, generator: BaseGenerator) -> None:
        self.width = w
        self.height = h
        self.goals = generator.get(w*h)
        self.marks: dict[str, set] = {} # {Teamid : {goals}}
    
    def get_user_view(self, userId) -> dict:
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
                "marks": self.marks}

class NonLockout(Board):
    """Alias for basic, unbiased board"""

class Lockout(Board):
    """Basic unbiased lockout board"""
    def mark(self, index: int, teamid: str) -> bool:
        if teamid not in self.marks: 
            self.marks[teamid] = {}

        if index in self.marks[teamid]: 
            return False
        else: 
            allmarked = set().union(*self.marks.values())
            if index in allmarked: 
                return False
            self.marks[teamid].add(index)
        return True

class Exploration(Board):
    """13x13 board with marks hidden between teams and only adjacent goals displayed."""