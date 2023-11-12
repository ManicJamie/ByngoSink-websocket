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
        """Provides a minimum amount of data on the board for display (used for unteamed users)"""
        return {"type": self.name, "width": self.width, "height": self.height,
                "game": self.game, "generatorName": self.generatorName}
    
    def get_team_view(self, teamId) -> dict:
        """Provides a view on the board for a given team."""
        return self.get_full_view()

    def get_full_view(self) -> dict:
        """Provides a complete view on all goals and marks"""
        return {"type": self.name, "width": self.width, "height": self.height,
                "game": self.game, "generatorName": self.generatorName,
                "goals": {i:g.get_repr() for i, g in enumerate(self.goals)},
                "marks": {t:list(g) for t, g in self.marks.items()}}
    
    def mark(self, index: int, teamid) -> bool:
        index = int(index)
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
    
    """Non-hidden formats, minimum == full""" 
    def get_minimum_view(self) -> dict: return self.get_full_view()
    def get_team_view(self, teamId) -> dict: return self.get_full_view()

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
    """13x13 board with marks hidden between teams and only adjacent goals displayed. Center->Corner"""
    name = "Exploration"
    base = {84}
    def __init__(self, generator: "T_GENERATOR", seed) -> None:
        super().__init__(13, 13, generator, seed)
    
    def get_minimum_view(self) -> dict:
        return {"type": self.name, "width": self.width, "height": self.height,
                "game": self.game, "generatorName": self.generatorName,
                "goals": {i:self.goals[i].get_repr() for i in self.base}}

    """Double blind marks (No other team marks seen), adjacent goals revealed"""
    def get_team_view(self, teamId) -> dict: 
        team_marks = self.marks.get(teamId, None)
        overall_seen = self.base.copy()
        for i in self.base:
            overall_seen.update(self._recurse_seen_goals(i, team_marks, overall_seen))

        return {"type": self.name, "width": self.width, "height": self.height,
                "game": self.game, "generatorName": self.generatorName,
                "goals": {i:self.goals[i].get_repr() for i in overall_seen},
                "marks": {teamId:list(team_marks)}}

    def _recurse_seen_goals(self, i, team_marks, seen:set):
        if i in team_marks:
            x = i % 13
            y = i // 13
            adj_xys = {(x - 1, y), (x + 1, y), (x, y + 1), (x, y - 1)}
            to_check = set()
            for xy in adj_xys:
                if xy[0] >= 0 and xy[0] <= 12 and xy[1] >= 0 and xy[1] <= 12:
                    index = xy[1] * 13 + xy[0]
                    if index not in seen: to_check.add(index)
            to_check.difference_update(seen) # don't check already seen values
            seen.update(to_check)
            for i in to_check:
                self._recurse_seen_goals(i, team_marks, seen)
        return seen

class GTTOS(Exploration):
    """13x13 board with marks hidden between teams and only adjacent goals displayed. Left->Right"""
    name="Get To The Other Side"
    base = {0, 13, 26, 39, 52, 65, 78, 91, 104, 117, 130, 143, 156}

ALIASES = {
    "Non-Lockout": Bingo,
    "Lockout": Lockout,
    "Exploration": Exploration,
    "GTTOS": GTTOS
}

def create_board(boardstr, generator: "T_GENERATOR", seed) -> Board:
    return ALIASES[boardstr](generator, seed)